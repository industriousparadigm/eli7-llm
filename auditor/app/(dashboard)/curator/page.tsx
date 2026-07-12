import { safeQuery } from "@/lib/db";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import Pagination from "@/components/Pagination";
import DiffView from "@/components/DiffView";
import { formatDateTime } from "@/lib/format";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 20;

type CuratorEvent = {
  commit_sha: string;
  ts: string;
  reason: string | null;
  files_changed: string[];
  diff: string | null;
};

export default async function CuratorPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  const [countResult, rowsResult] = await Promise.all([
    safeQuery<{ count: string }>(`select count(*)::text as count from curator_events`),
    safeQuery<CuratorEvent>(
      `select commit_sha, ts, reason, files_changed, diff
       from curator_events
       order by ts desc
       limit $1 offset $2`,
      [PAGE_SIZE, offset]
    ),
  ]);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Curator timeline</h1>
          <p className="subtitle">
            The audit trail of how Nuvem&apos;s knowledge of Diana evolved — one entry per curator commit.
          </p>
        </div>
      </div>

      {!rowsResult.ok ? (
        <ErrorState message={rowsResult.error} />
      ) : rowsResult.rows.length === 0 ? (
        <EmptyState
          title="No curator events yet"
          detail="Nothing has been committed by the curator pipeline yet."
        />
      ) : (
        <>
          <div className="stack">
            {rowsResult.rows.map((event) => (
              <details className="curator-event" key={event.commit_sha}>
                <summary>
                  <div className="curator-event-main">
                    <div className="curator-event-reason">
                      {event.reason || "(no reason recorded)"}
                    </div>
                    <div className="curator-event-files">
                      {event.files_changed.length} file
                      {event.files_changed.length === 1 ? "" : "s"} changed —{" "}
                      {event.files_changed.join(", ") || "none listed"}
                    </div>
                  </div>
                  <div className="curator-event-side">
                    {formatDateTime(event.ts)}
                    <div className="curator-event-sha">{event.commit_sha.slice(0, 7)}</div>
                  </div>
                </summary>
                <div className="curator-event-body">
                  <DiffView diff={event.diff} />
                </div>
              </details>
            ))}
          </div>
          {countResult.ok && (
            <Pagination
              basePath="/curator"
              page={page}
              totalPages={Math.max(1, Math.ceil(Number(countResult.rows[0]?.count ?? 0) / PAGE_SIZE))}
            />
          )}
        </>
      )}
    </>
  );
}
