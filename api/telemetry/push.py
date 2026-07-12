"""Best-effort mirror of Eli7's live data into Supabase, read by the auditor
dashboard. Source of truth stays local (conversation JSONL logs + the
diana-memory git repo) - this module only ever pushes a copy outward.

Hard rule: telemetry must NEVER break Diana's answer path or the curator.
Every public function here swallows its own exceptions. On failure it tries to
leave a breadcrumb in pipeline_health; if even that fails, it just logs and
returns. Nothing in this module ever raises to its caller.

Schema is applied already (see telemetry/schema.sql, not touched by this
module) with unique constraints on the natural keys, so every insert here uses
ON CONFLICT DO NOTHING - safe to re-push the same data any number of times.
"""

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("telemetry")

# Local dev / the Pi both keep the Supabase creds in a dotfile outside the
# repo (see telemetry/README.md for the Pi path). override=False so a
# SUPABASE_DB_URL already exported in the real environment always wins.
_ENV_FILE = Path(os.getenv("SUPABASE_ENV_FILE", "~/.eli7/supabase.env")).expanduser()
load_dotenv(_ENV_FILE, override=False)

DB_URL = os.getenv("SUPABASE_DB_URL")

try:
    import psycopg
    _HAVE_DRIVER = True
except ImportError:
    _HAVE_DRIVER = False

# Doc names tracked in the diana-memory repo (memory_repo.SEED_CONTENT) that
# push_curator_events() will snapshot. Kept as a local constant rather than an
# import from api/ - telemetry only owns telemetry/, and this list is stable
# (it's the memory system's fixed doc set, documented in schema.sql's
# memory_snapshots comment).
DOC_FILES = ["about-diana.md", "memory.md", "people.md", "recent.md"]


def _connect():
    """A fresh connection, or None if the driver/URL/network isn't available.
    Never raises - every caller treats None as "skip, telemetry is down"."""
    if not _HAVE_DRIVER:
        logger.warning("telemetry: psycopg not installed, skipping")
        return None
    if not DB_URL:
        logger.warning("telemetry: SUPABASE_DB_URL not set, skipping")
        return None
    try:
        return psycopg.connect(DB_URL, connect_timeout=5)
    except Exception:
        logger.exception("telemetry: failed to connect to Supabase")
        return None


def _parse_ts(ts):
    """Callers may pass a datetime or an ISO 8601 string (git's %aI, or the
    JSONL logs' datetime.isoformat()) - normalize to a datetime so psycopg
    never has to guess how to adapt a bare string into timestamptz."""
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return ts  # let it surface naturally rather than guess further
    return ts


def health(component: str, status: str, detail: str | None = None) -> None:
    """Best-effort pipeline_health row (heartbeat or error)."""
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into pipeline_health (component, status, detail) "
                    "values (%s, %s, %s)",
                    (component, status, detail),
                )
    except Exception:
        logger.exception("telemetry: health() failed to write")
    finally:
        conn.close()


def _report_failure(component: str, detail: str) -> None:
    """Try to leave a pipeline_health breadcrumb for a failure in some other
    push function. Itself never raises - if the DB is unreachable there's
    nowhere left to report to, so just log."""
    try:
        health(component, "error", detail)
    except Exception:
        logger.exception("telemetry: could not even record the failure")


def push_conversation(
    session_id: str | None,
    ts,
    question: str,
    response: str,
    language: str | None,
    source: str = "pi",
) -> None:
    """Mirror one Q&A exchange into `conversations`. `ts` may be a datetime or
    an ISO 8601 string. Idempotent via the (session_id, ts, question) unique
    constraint."""
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into conversations
                        (session_id, ts, question, response, language,
                         question_len, response_len, source)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (session_id, ts, question) do nothing
                    """,
                    (
                        session_id,
                        _parse_ts(ts),
                        question,
                        response,
                        language,
                        len(question or ""),
                        len(response or ""),
                        source,
                    ),
                )
    except Exception:
        logger.exception("telemetry: push_conversation failed")
        _report_failure("push", f"push_conversation failed for session {session_id}")
    finally:
        conn.close()


def _git(memory_dir: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=memory_dir, capture_output=True, text=True
    )
    return result.stdout


def push_curator_events(memory_dir) -> None:
    """Mirror any diana-memory commits not yet in curator_events: one
    curator_events row per new commit (sha, timestamp, commit message as
    `reason`, changed doc files, full diff), plus one memory_snapshots row per
    changed doc holding its full content AT that commit.

    Idempotent - re-running only touches commits whose sha isn't already in
    curator_events. Each commit is pushed inside its own transaction, so a
    failure partway through a single commit rolls back cleanly and gets
    retried whole on the next call, rather than leaving a curator_events row
    with missing snapshots.
    """
    memory_dir = Path(memory_dir).expanduser()
    if not (memory_dir / ".git").exists():
        logger.warning("telemetry: no git repo at %s, skipping curator push", memory_dir)
        return

    conn = _connect()
    if conn is None:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("select commit_sha from curator_events")
            known_shas = {row[0] for row in cur.fetchall()}

        log_out = _git(memory_dir, ["log", "--reverse", "--format=%H|%aI|%s"])
        for line in log_out.splitlines():
            if not line.strip():
                continue
            sha, iso_ts, message = line.split("|", 2)
            if sha in known_shas:
                continue
            try:
                _push_one_commit(conn, memory_dir, sha, iso_ts, message)
                conn.commit()
            except Exception:
                conn.rollback()
                logger.exception("telemetry: failed to push commit %s", sha)
                _report_failure("push", f"push_curator_events failed on {sha[:8]}")
    except Exception:
        logger.exception("telemetry: push_curator_events failed")
        _report_failure("push", "push_curator_events failed")
    finally:
        conn.close()


def _push_one_commit(conn, memory_dir: Path, sha: str, iso_ts: str, message: str) -> None:
    """Stages one commit's rows on `conn` - does NOT commit/rollback itself.
    The caller (push_curator_events) owns the transaction boundary, since
    psycopg's `with conn:` closes the connection on exit and this is called
    repeatedly against one shared connection across many commits."""
    changed_raw = _git(memory_dir, ["show", "--name-only", "--format=", sha]).splitlines()
    changed = [f for f in changed_raw if f.strip() in DOC_FILES]
    diff = _git(memory_dir, ["show", sha]) if changed else None
    ts = _parse_ts(iso_ts)

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into curator_events (commit_sha, ts, reason, files_changed, diff)
            values (%s, %s, %s, %s, %s)
            on conflict (commit_sha) do nothing
            """,
            (sha, ts, message, changed, diff),
        )
        for fname in changed:
            content = _git(memory_dir, ["show", f"{sha}:{fname}"])
            doc = fname[:-3]  # "recent.md" -> "recent"
            cur.execute(
                """
                insert into memory_snapshots (commit_sha, ts, doc, content)
                values (%s, %s, %s, %s)
                on conflict (commit_sha, doc) do nothing
                """,
                (sha, ts, doc, content),
            )
