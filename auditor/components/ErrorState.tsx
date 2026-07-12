export default function ErrorState({
  title = "Couldn't load this data",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="state-box error">
      <h3>{title}</h3>
      <p>The query failed. This is usually the database being unreachable or misconfigured.</p>
      <code>{message}</code>
    </div>
  );
}
