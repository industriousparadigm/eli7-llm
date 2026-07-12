export type PillTone = "ok" | "warn" | "danger" | "neutral";

export default function StatusPill({
  tone,
  label,
}: {
  tone: PillTone;
  label: string;
}) {
  return (
    <span className={`pill pill-${tone}`}>
      {tone !== "neutral" && <span className="pill-dot" />}
      {label}
    </span>
  );
}
