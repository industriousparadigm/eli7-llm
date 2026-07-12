import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { formatDateTime } from "@/lib/format";

export type MemoryRow = {
  doc: string;
  content: string;
  commit_sha: string;
  ts: string | Date;
};

export default function MarkdownCard({
  title,
  row,
}: {
  title: string;
  row: MemoryRow | undefined;
}) {
  return (
    <div className="card">
      <div className="memory-card-header">
        <h2>{title}</h2>
        {row && (
          <div className="meta">
            {row.commit_sha.slice(0, 7)}
            <br />
            {formatDateTime(row.ts)}
          </div>
        )}
      </div>
      {row ? (
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{row.content}</ReactMarkdown>
        </div>
      ) : (
        <p style={{ color: "var(--text-faint)", fontSize: 13 }}>
          Not generated yet.
        </p>
      )}
    </div>
  );
}
