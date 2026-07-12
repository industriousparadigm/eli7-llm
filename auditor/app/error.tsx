"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="login-shell">
      <div className="state-box error" style={{ maxWidth: 480 }}>
        <h3>Something went wrong</h3>
        <p>The page failed to render. This is a bug in the dashboard itself, not a data issue.</p>
        <code>{error.message}</code>
        <button className="btn" style={{ marginTop: 16 }} onClick={() => reset()}>
          Try again
        </button>
      </div>
    </div>
  );
}
