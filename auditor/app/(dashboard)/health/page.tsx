import { safeQuery } from "@/lib/db";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusPill, { type PillTone } from "@/components/StatusPill";
import { formatDateTime, formatRelative, freshnessLevel } from "@/lib/format";

export const dynamic = "force-dynamic";

type HealthRow = {
  component: string;
  status: string;
  detail: string | null;
  ts: string;
};

function freshnessTone(ts: string | Date | null): PillTone {
  const level = freshnessLevel(ts);
  if (level === "ok") return "ok";
  if (level === "warn") return "warn";
  return "danger";
}

function componentTone(row: HealthRow): PillTone {
  if (row.status === "error") return "danger";
  return freshnessTone(row.ts);
}

function worstTone(tones: PillTone[]): PillTone {
  if (tones.includes("danger")) return "danger";
  if (tones.includes("warn")) return "warn";
  return "ok";
}

export default async function HealthPage() {
  const [healthResult, lastConvResult, lastCuratorResult] = await Promise.all([
    safeQuery<HealthRow>(
      `select distinct on (component) component, status, detail, ts
       from pipeline_health
       order by component, ts desc`
    ),
    safeQuery<{ last: string | null }>(`select max(ts) as last from conversations`),
    safeQuery<{ last: string | null }>(`select max(ts) as last from curator_events`),
  ]);

  const anyError = !healthResult.ok || !lastConvResult.ok || !lastCuratorResult.ok;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Health</h1>
          <p className="subtitle">Are the conversation, curator, and push pipelines actually flowing?</p>
        </div>
      </div>

      {anyError ? (
        <ErrorState
          message={
            (!healthResult.ok && healthResult.error) ||
            (!lastConvResult.ok && lastConvResult.error) ||
            (!lastCuratorResult.ok && lastCuratorResult.error) ||
            "Unknown error"
          }
        />
      ) : (
        <HealthBody
          healthRows={healthResult.ok ? healthResult.rows : []}
          lastConversation={lastConvResult.ok ? lastConvResult.rows[0]?.last ?? null : null}
          lastCuratorEvent={lastCuratorResult.ok ? lastCuratorResult.rows[0]?.last ?? null : null}
        />
      )}
    </>
  );
}

function HealthBody({
  healthRows,
  lastConversation,
  lastCuratorEvent,
}: {
  healthRows: HealthRow[];
  lastConversation: string | null;
  lastCuratorEvent: string | null;
}) {
  const componentTones = healthRows.map(componentTone);
  const overall = worstTone([
    ...componentTones,
    freshnessTone(lastConversation),
    freshnessTone(lastCuratorEvent),
  ]);

  const overallCopy: Record<PillTone, string> = {
    ok: "All pipelines flowing",
    warn: "Getting stale — worth a look",
    danger: "Attention needed",
    neutral: "Unknown",
  };

  return (
    <>
      <div className={`health-summary ${overall}`}>
        <StatusPill tone={overall} label={overall === "ok" ? "OK" : overall === "warn" ? "Warn" : "Down"} />
        <strong>{overallCopy[overall]}</strong>
      </div>

      <div className="freshness-grid">
        <div className="freshness-tile">
          <div className="label">Last conversation</div>
          <div className="value">{formatRelative(lastConversation)}</div>
          {lastConversation && <div className="sub">{formatDateTime(lastConversation)}</div>}
        </div>
        <div className="freshness-tile">
          <div className="label">Last curator event</div>
          <div className="value">{formatRelative(lastCuratorEvent)}</div>
          {lastCuratorEvent && <div className="sub">{formatDateTime(lastCuratorEvent)}</div>}
        </div>
      </div>

      {healthRows.length === 0 ? (
        <EmptyState
          title="No pipeline heartbeats recorded yet"
          detail="Nothing has reported to pipeline_health yet."
        />
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="health-table">
            <thead>
              <tr>
                <th>Component</th>
                <th>Status</th>
                <th>Last seen</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {healthRows.map((row) => {
                const tone = componentTone(row);
                return (
                  <tr key={row.component}>
                    <td>{row.component}</td>
                    <td>
                      <StatusPill
                        tone={tone}
                        label={tone === "ok" ? "OK" : tone === "warn" ? "Stale" : row.status === "error" ? "Error" : "Stale"}
                      />
                    </td>
                    <td>{formatRelative(row.ts)}</td>
                    <td className="detail">{row.detail || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
