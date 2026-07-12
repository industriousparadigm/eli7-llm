-- DianasNuvem — Eli7 auditor backend schema (Supabase Postgres)
-- Source of truth stays on the Pi (conversation JSONL) + the diana-memory git repo.
-- These tables are the queryable MIRROR the auditor dashboard reads.

-- Every question/answer exchange with Nuvem.
create table if not exists conversations (
  id            bigserial primary key,
  session_id    text,
  ts            timestamptz not null,
  question      text not null,
  response      text not null,
  language      text,
  question_len  int,
  response_len  int,
  source        text not null default 'pi',   -- 'pi' | 'local'
  inserted_at   timestamptz not null default now(),
  unique (session_id, ts, question)            -- idempotent backfill / re-push
);
create index if not exists conversations_ts_idx on conversations (ts desc);

-- One row per curator commit in the diana-memory repo (the audit trail of what
-- the AI's knowledge of Diana became, and WHY — the commit message).
create table if not exists curator_events (
  id            bigserial primary key,
  commit_sha    text not null unique,
  ts            timestamptz not null,
  reason        text,                          -- the curator's own commit message ("why")
  files_changed text[] not null default '{}',
  diff          text,
  inserted_at   timestamptz not null default now()
);
create index if not exists curator_events_ts_idx on curator_events (ts desc);

-- Full content of each memory doc at each commit (history + latest-state view).
create table if not exists memory_snapshots (
  id            bigserial primary key,
  commit_sha    text not null,
  ts            timestamptz not null,
  doc           text not null,                 -- 'about-diana' | 'memory' | 'people' | 'recent'
  content       text not null,
  inserted_at   timestamptz not null default now(),
  unique (commit_sha, doc)
);
create index if not exists memory_snapshots_doc_ts_idx on memory_snapshots (doc, ts desc);

-- Latest content of each doc, for the dashboard "what Nuvem knows now" panel.
create or replace view memory_latest as
select distinct on (doc) doc, content, commit_sha, ts
from memory_snapshots
order by doc, ts desc;

-- Pipeline heartbeat + errors, so the dashboard can show health honestly.
create table if not exists pipeline_health (
  id          bigserial primary key,
  ts          timestamptz not null default now(),
  component   text not null,                   -- 'answer' | 'curator' | 'push' | 'suggestions_cron'
  status      text not null,                   -- 'ok' | 'error'
  detail      text
);
create index if not exists pipeline_health_ts_idx on pipeline_health (ts desc);

-- SECURITY: the publishable/anon key is public (ships in the browser bundle), so the
-- Supabase REST API is a second door past the dashboard login. Enable RLS with NO
-- policies => the public key reads nothing via REST; the dashboard's server-side
-- connection (owner role, via SUPABASE_DB_URL) bypasses RLS and still reads everything.
alter table conversations    enable row level security;
alter table curator_events   enable row level security;
alter table memory_snapshots enable row level security;
alter table pipeline_health  enable row level security;
-- Normal views run with definer rights and would leak past base-table RLS; make the
-- view respect the querying role's RLS instead.
alter view memory_latest set (security_invoker = on);
