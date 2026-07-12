export default function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail?: string;
}) {
  return (
    <div className="state-box">
      <h3>{title}</h3>
      {detail && <p>{detail}</p>}
    </div>
  );
}
