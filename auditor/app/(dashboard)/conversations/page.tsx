import { safeQuery } from "@/lib/db";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import Pagination from "@/components/Pagination";
import { dayKey, formatDayHeading, formatTime } from "@/lib/format";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 25;

type ConversationRow = {
  id: number;
  session_id: string | null;
  ts: string;
  question: string;
  response: string;
  language: string | null;
  source: string;
};

export default async function ConversationsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const params = await searchParams;
  const q = (params.q ?? "").trim();
  const page = Math.max(1, Number(params.page) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  const [countResult, rowsResult] = await Promise.all([
    safeQuery<{ count: string }>(
      `select count(*)::text as count
       from conversations
       where ($1 = '' or question ilike '%' || $1 || '%' or response ilike '%' || $1 || '%')`,
      [q]
    ),
    safeQuery<ConversationRow>(
      `select id, session_id, ts, question, response, language, source
       from conversations
       where ($1 = '' or question ilike '%' || $1 || '%' or response ilike '%' || $1 || '%')
       order by ts desc
       limit $2 offset $3`,
      [q, PAGE_SIZE, offset]
    ),
  ]);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Conversations</h1>
          <p className="subtitle">Every exchange between Diana and Nuvem, newest first.</p>
        </div>
        <form className="search-form" method="get">
          <input
            type="search"
            name="q"
            defaultValue={q}
            placeholder="Search questions or responses…"
          />
          <button type="submit" className="btn">Search</button>
        </form>
      </div>

      {!rowsResult.ok ? (
        <ErrorState message={rowsResult.error} />
      ) : rowsResult.rows.length === 0 ? (
        <EmptyState
          title={q ? "No matching conversations" : "No conversations yet"}
          detail={
            q
              ? "Try a different search term."
              : "Nothing has been logged from Nuvem yet. This fills in once the backfill/live pipeline runs."
          }
        />
      ) : (
        <>
          <ConversationList rows={rowsResult.rows} />
          {countResult.ok && (
            <Pagination
              basePath="/conversations"
              page={page}
              totalPages={Math.max(1, Math.ceil(Number(countResult.rows[0]?.count ?? 0) / PAGE_SIZE))}
              extraParams={{ q: q || undefined }}
            />
          )}
        </>
      )}
    </>
  );
}

function ConversationList({ rows }: { rows: ConversationRow[] }) {
  const groups: { key: string; heading: string; items: ConversationRow[] }[] = [];

  for (const row of rows) {
    const key = dayKey(row.ts);
    const last = groups[groups.length - 1];
    if (last && last.key === key) {
      last.items.push(row);
    } else {
      groups.push({ key, heading: formatDayHeading(row.ts), items: [row] });
    }
  }

  return (
    <>
      {groups.map((group) => (
        <div className="day-group" key={group.key}>
          <div className="day-heading">{group.heading}</div>
          <div className="stack">
            {group.items.map((row) => (
              <article className="exchange" key={row.id}>
                <div className="exchange-meta">
                  <span className="exchange-time">{formatTime(row.ts)}</span>
                  {row.language && <span className="pill pill-neutral">{row.language}</span>}
                  <span className="pill pill-neutral">{row.source}</span>
                  {row.session_id && (
                    <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)" }}>
                      {row.session_id.slice(0, 8)}
                    </span>
                  )}
                </div>
                <div className="exchange-body">
                  <p className="exchange-question">{row.question}</p>
                  <p className="exchange-response">{row.response}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
