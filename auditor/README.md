# Eli7 Auditor

A private monitoring dashboard for **DianasNuvem** (the Eli7 kid-safe AI companion). Not
kid-facing — this is for Diogo (the parent) to see what Diana and Nuvem are actually doing:
every conversation, what Nuvem currently "knows" about Diana, the audit trail of how that
knowledge evolved, and whether the pipelines behind it are healthy.

Next.js 16 App Router + TypeScript. Reads a Supabase Postgres database server-side (via `pg`,
no ORM). No client ever touches the database directly.

## Panels

- **Conversations** (`/conversations`) — every Q&A exchange, newest first, grouped by day, with
  free-text search and pagination.
- **O que a Nuvem sabe** (`/memory`) — the four current memory docs (about-diana, memory, people,
  recent) rendered as markdown cards, from the `memory_latest` view.
- **Curator timeline** (`/curator`) — one entry per curator commit: the reason, files changed, and
  a collapsible diff. The audit trail of how Nuvem's understanding of Diana changed over time.
- **Health** (`/health`) — latest heartbeat per pipeline component plus freshness ("how long since
  the last conversation / curator event") with a green/amber/red read on whether things are
  actually flowing.

Every DB read is wrapped (`lib/db.ts#safeQuery`) so a failed query renders an inline error card,
never a crashed page. Empty tables render an explicit empty state instead of looking broken.

## Environment variables

Copy `.env.example` to `.env.local` for local dev, or set these in Vercel:

| Variable | Description |
|---|---|
| `SUPABASE_DB_URL` | Postgres connection string for the Supabase **session pooler** (IPv4-safe). Same value used by the Pi push script — see `/Users/diogo/.eli7/supabase.env` locally. |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project API URL. Public by design. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/publishable key. Public by design — it's meant to ship in the client bundle. |
| `AUDITOR_ALLOWED_EMAILS` | Comma-separated allowlist gating the dashboard. Defaults to `dsgmcosta@gmail.com,miragaia.mariana@gmail.com` if unset. |

Nothing else is required. The app doesn't call any LLM or external API — it only reads the
telemetry tables the main Eli7 app / curator pipeline writes to (`conversations`,
`curator_events`, `memory_snapshots`, `memory_latest` view, `pipeline_health` — schema at
`../telemetry/schema.sql`).

## Auth

Supabase Auth with an email **magic link** (no password, no code to type, no OAuth app to
manage) plus a 2-email allowlist on top. Supabase's default magic-link email template works
out of the box — the custom-template editor (needed for a code-style email) is plan-gated,
the plain magic link isn't.

1. `/login` — enter your email. A Server Action (`requestMagicLink` in `lib/auth-actions.ts`)
   checks the email against `AUDITOR_ALLOWED_EMAILS` **before** calling
   `supabase.auth.signInWithOtp()` with `emailRedirectTo` pointed at `/auth/callback` — a
   non-allowlisted address never gets a link sent to it. The redirect origin is derived from
   the request at runtime (works on localhost and the deployed Vercel URL alike), never
   hardcoded.
2. The link lands on `app/auth/callback/route.ts`, which exchanges the `code` query param for a
   session via `supabase.auth.exchangeCodeForSession()` (sets the `@supabase/ssr` session
   cookie), then re-checks the allowlist against the *authenticated* email — if allowed,
   redirects to `/conversations`; if not, signs out and redirects to
   `/login?error=not-authorized`. A missing or invalid code redirects back to `/login` with an
   error too.
3. `proxy.ts` (Next 16's renamed `middleware.ts`) calls `lib/supabase/middleware.ts#updateSession`
   on every route except `/login`: it refreshes the Supabase session cookie, reads the JWT claims,
   and redirects to `/login` unless the email is on the allowlist. This is the fast, optimistic
   check.
4. `app/(dashboard)/layout.tsx` re-checks with a real network call (`supabase.auth.getUser()`) —
   the authoritative check, so a stale or forged cookie can never reach the data even if the proxy
   gate were bypassed.

The Supabase project's Auth > URL Configuration must list this app's origin(s) in `site_url` /
`uri_allow_list` (the Vercel URL, plus `http://localhost:<port>` for local dev) or the
magic-link redirect is rejected.

The allowlist logic lives in `lib/auth.ts` (`isEmailAllowed`, `getPostAuthRedirect`), covered by
a small unit test — `npm test`.

## Local development

```bash
npm install
cp .env.example .env.local   # fill in SUPABASE_DB_URL + the Supabase Auth vars
npm run dev
npm test                     # unit test for the email allowlist
```

Open http://localhost:3000 — you'll land on `/login` first.

```bash
npm run build   # production build, must pass before shipping
npm run start   # serve the production build locally
```

## Deploying to Vercel

This is a separate app from the rest of `soft-terminal-llm` (which deploys to the Pi, not
Vercel) — it needs its own Vercel project.

1. `vercel whoami` — confirm you're on the **personal** account (`dsgmcosta`), not the Okra one
   (`sw-5805`). This is a personal project.
2. From this directory: `vercel link` (first time) to create/link the project.
3. Set env vars — use `printf`, never `echo`, to avoid a trailing-newline bug that silently
   breaks values:
   ```bash
   printf '%s' "$SUPABASE_DB_URL" | vercel env add SUPABASE_DB_URL production
   printf '%s' 'https://hvxvaqbubeqwepnhuebx.supabase.co' | vercel env add NEXT_PUBLIC_SUPABASE_URL production --no-sensitive
   printf '%s' 'the-anon-key' | vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production --no-sensitive
   printf '%s' 'dsgmcosta@gmail.com,miragaia.mariana@gmail.com' | vercel env add AUDITOR_ALLOWED_EMAILS production
   ```
   `NEXT_PUBLIC_*` vars need `--no-sensitive` — otherwise a prebuilt CLI deploy bakes an empty
   string into the client bundle instead of the real value. `SUPABASE_DB_URL` and
   `AUDITOR_ALLOWED_EMAILS` are server-only and read at runtime, no flag needed.
4. `vercel --prod` to ship. Verify with `vercel env ls` and by visiting the deployed URL's
   `/login` page.
5. Confirm the production domain actually serves the new deployment (a bare `vercel --prod` can
   leave two deployment URLs — the build and an aliased copy — inspect the production domain to
   be sure).
