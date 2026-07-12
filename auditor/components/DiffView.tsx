function classifyLine(line: string): string {
  if (line.startsWith("@@")) return "diff-hunk";
  if (line.startsWith("+++") || line.startsWith("---")) return "diff-meta";
  if (line.startsWith("+")) return "diff-add";
  if (line.startsWith("-")) return "diff-remove";
  return "diff-context";
}

export default function DiffView({ diff }: { diff: string | null }) {
  if (!diff || diff.trim() === "") {
    return <p style={{ color: "var(--text-faint)", fontSize: 13 }}>No diff recorded for this commit.</p>;
  }

  const lines = diff.replace(/\r\n/g, "\n").split("\n");

  return (
    <div className="diff-view">
      {lines.map((line, i) => (
        <div key={i} className={`diff-line ${classifyLine(line)}`}>
          {line.length ? line : " "}
        </div>
      ))}
    </div>
  );
}
