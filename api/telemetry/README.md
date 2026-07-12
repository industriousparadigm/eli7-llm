# Telemetry

Mirrors Eli7's live data into Supabase, so the auditor dashboard can read it
without ever touching the real sources of truth (the Pi's conversation JSONL
logs, and the `diana-memory` git repo). Nothing here is authoritative - if
this whole layer disappeared, Diana's answers and the curator would keep
working exactly as before.

**Hard rule: telemetry must never break Diana's answer path or the curator.**
Every function in `push.py` swallows its own exceptions. A failure tries to
leave a breadcrumb in `pipeline_health`; if even that fails, it just logs.
Nothing here ever raises to its caller.

## Files

- **`schema.sql`** - the applied Supabase schema (owned elsewhere, not
  touched by this code). Tables: `conversations`, `curator_events`,
  `memory_snapshots` (+ `memory_latest` view), `pipeline_health`.
- **`push.py`** - the library. `push_conversation(...)` mirrors one Q&A
  exchange; `push_curator_events(memory_dir)` mirrors any diana-memory git
  commits not yet in Supabase (one `curator_events` row per commit, one
  `memory_snapshots` row per doc it changed); `health(component, status,
  detail)` writes a `pipeline_health` row directly. All idempotent via the
  schema's unique constraints (`ON CONFLICT DO NOTHING`).
- **`backfill.py`** - one-shot script to mirror everything that existed
  before telemetry existed. See below.
- **`__init__.py`** - empty, just makes `telemetry` importable as
  `from telemetry import push` from `api/main.py` and `api/curator.py`.

## Wiring (in api/)

`api/main.py` and `api/curator.py` import `telemetry.push` defensively:

```python
sys.path.insert(0, <repo root>)
try:
    from telemetry import push as telemetry_push
except ImportError:
    telemetry_push = None
```

Every call site checks `if telemetry_push:` first, so a missing/unimportable
telemetry package degrades to a silent no-op rather than an error.

- **`main.py` `/ask`**: after logging the exchange and queuing the curator
  background task, queues a `push_conversation(...)` background task with the
  same fire-and-forget shape.
- **`curator.py` `_run_curator`**: after a successful `commit_all(...)`, calls
  `push_curator_events(memory.get_memory_dir())` (via `asyncio.to_thread`, so
  the blocking DB calls don't block the event loop) so the new commit shows
  up in Supabase right after curation, not just at the next backfill.

## Env needed

- `SUPABASE_DB_URL` - the session pooler URL (IPv4-safe), pointing at the
  `hvxvaqbubeqwepnhuebx` project. Loaded from `~/.eli7/supabase.env` by
  default (override the path with `SUPABASE_ENV_FILE`); an already-exported
  `SUPABASE_DB_URL` in the real environment always wins.
- `TELEMETRY_SOURCE` - tags pushed `conversations` rows (`'pi'` or
  `'local'`). Defaults to `'local'` (safe for dev). **The Pi deploy must set
  `TELEMETRY_SOURCE=pi`** so the dashboard can tell real usage apart from
  local testing.
- Driver: `psycopg[binary]` (added to `api/requirements.txt`).

## Running the backfill

One-shot, safe to re-run any number of times (same idempotency as the live
push path):

```bash
# Real run, on the Pi, once telemetry is deployed there:
api/.venv/bin/python telemetry/backfill.py
# -> --logs-dir defaults to ~/soft-terminal-llm/logs, --source defaults to 'pi'

# Local testing - point at any local logs folder, tag it as local data:
api/.venv/bin/python telemetry/backfill.py --logs-dir ./logs --source local
api/.venv/bin/python telemetry/backfill.py --memory-dir ~/diana-memory --skip-conversations
```

Flags: `--logs-dir`, `--memory-dir`, `--source {pi,local}`,
`--skip-conversations`, `--skip-curator`. `--logs-dir` and `--memory-dir` also
read `LOGS_BACKFILL_DIR` / `DIANA_MEMORY_DIR` env vars as defaults.

## Pi deploy note

Two things need to be true before telemetry works on the Pi - until they are,
it silently no-ops (by design, per the hard rule above) rather than breaking
anything:

1. **Driver installed.** `psycopg[binary]` is in `api/requirements.txt`, so a
   normal `pip install -r requirements.txt` / Docker image rebuild picks it
   up automatically.
2. **`telemetry/` needs to be reachable from inside the API container.**
   `docker-compose.yml`'s dev `api` service only mounts `./api:/app` (and the
   `Dockerfile`'s build context is `./api`), so today the `telemetry/`
   directory - a sibling of `api/`, not inside it - is invisible inside the
   container. The `sys.path.insert(...)` trick in `main.py`/`curator.py`
   only helps when running directly on the host (as this was verified
   locally); it does nothing if the file literally isn't present in the
   image/volume. Until `docker-compose.yml` (or the `Dockerfile`) is updated
   to mount or copy `telemetry/` alongside `api/`, `import telemetry` will
   fail inside the container and every push above becomes a no-op - not a
   crash, just silently missing data. This wasn't fixed here since
   `docker-compose.yml`/`Dockerfile` are outside this build's scope - flag it
   before relying on telemetry data appearing from the deployed Pi.
3. **`SUPABASE_DB_URL` and `TELEMETRY_SOURCE=pi`** need to reach the
   container's environment (e.g. via `.env`/`.env.production` and
   `docker-compose.prod.yml`'s `env_file`/`environment` block) the same way
   `ANTHROPIC_API_KEY` already does.
