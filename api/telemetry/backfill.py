"""One-shot backfill: mirrors existing local data into Supabase.

Two independent, idempotent jobs (each safe to re-run - same unique
constraints and ON CONFLICT DO NOTHING as the live push path in push.py):

  1. Conversation JSONL logs -> `conversations`.
  2. The diana-memory git repo's full commit history -> `curator_events` +
     `memory_snapshots`, via push.push_curator_events (same function the live
     curator calls after every new commit).

NOTE on the conversation logs: the real logs live on the Pi (see
ConversationLogger in api/main.py - LOGS_DIR, default ~/soft-terminal-llm/logs,
one conversations_YYYYMMDD.jsonl per day). The real backfill run happens THERE
at deploy time, with the default --logs-dir and --source=pi. For local
testing, point --logs-dir at any local logs folder (this repo has
logs/*.jsonl and api/logs/*.jsonl from earlier dev sessions) and pass
--source local so the dashboard can tell test data apart from the real feed.

Usage:
    python telemetry/backfill.py
    python telemetry/backfill.py --logs-dir ./logs --source local
    python telemetry/backfill.py --skip-conversations
    python telemetry/backfill.py --memory-dir ~/diana-memory --skip-conversations
"""

import argparse
import glob
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from telemetry import push  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("telemetry.backfill")

DEFAULT_LOGS_DIR = os.getenv("LOGS_BACKFILL_DIR", "~/soft-terminal-llm/logs")
DEFAULT_MEMORY_DIR = os.getenv("DIANA_MEMORY_DIR", "~/diana-memory")


def backfill_conversations(logs_dir: Path, source: str) -> int:
    files = sorted(glob.glob(str(logs_dir / "*.jsonl")))
    pushed = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("skipping unparseable line %d in %s", line_num, path)
                    continue
                push.push_conversation(
                    session_id=entry.get("session_id"),
                    ts=entry.get("timestamp"),
                    question=entry.get("question", ""),
                    response=entry.get("response", ""),
                    language=entry.get("language"),
                    source=source,
                )
                pushed += 1
    return pushed


def main():
    parser = argparse.ArgumentParser(
        description="Backfill Supabase telemetry from local logs + the diana-memory repo."
    )
    parser.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR, help="Directory of conversations_*.jsonl files")
    parser.add_argument("--memory-dir", default=DEFAULT_MEMORY_DIR, help="Path to the diana-memory git repo")
    parser.add_argument("--source", default="pi", choices=["pi", "local"], help="Tag conversations rows with this source")
    parser.add_argument("--skip-conversations", action="store_true")
    parser.add_argument("--skip-curator", action="store_true")
    args = parser.parse_args()

    logs_dir = Path(args.logs_dir).expanduser()
    memory_dir = Path(args.memory_dir).expanduser()

    if not args.skip_conversations:
        if logs_dir.exists():
            n = backfill_conversations(logs_dir, args.source)
            logger.info("backfilled %d conversation rows from %s (source=%s)", n, logs_dir, args.source)
        else:
            logger.warning("logs dir %s does not exist, skipping conversations backfill", logs_dir)

    if not args.skip_curator:
        if (memory_dir / ".git").exists():
            push.push_curator_events(memory_dir)
            logger.info("pushed curator events + memory snapshots from %s", memory_dir)
        else:
            logger.warning("no git repo at %s, skipping curator backfill", memory_dir)


if __name__ == "__main__":
    main()
