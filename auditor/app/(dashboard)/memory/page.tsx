import { safeQuery } from "@/lib/db";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import MarkdownCard, { type MemoryRow } from "@/components/MarkdownCard";

export const dynamic = "force-dynamic";

const DOC_ORDER = ["about-diana", "memory", "people", "recent"];
const DOC_LABELS: Record<string, string> = {
  "about-diana": "About Diana",
  memory: "Memory",
  people: "People",
  recent: "Recent",
};

export default async function MemoryPage() {
  const result = await safeQuery<MemoryRow>(
    `select doc, content, commit_sha, ts from memory_latest`
  );

  return (
    <>
      <div className="page-header">
        <div>
          <h1>O que a Nuvem sabe</h1>
          <p className="subtitle">The four memory docs Nuvem currently holds about Diana.</p>
        </div>
      </div>

      {!result.ok ? (
        <ErrorState message={result.error} />
      ) : result.rows.length === 0 ? (
        <EmptyState
          title="No memory generated yet"
          detail="The curator hasn't produced any memory snapshots yet."
        />
      ) : (
        <MemoryGrid rows={result.rows} />
      )}
    </>
  );
}

function MemoryGrid({ rows }: { rows: MemoryRow[] }) {
  const byDoc = new Map(rows.map((r) => [r.doc, r]));
  return (
    <div className="grid-cards">
      {DOC_ORDER.map((doc) => (
        <MarkdownCard key={doc} title={DOC_LABELS[doc] ?? doc} row={byDoc.get(doc)} />
      ))}
    </div>
  );
}
