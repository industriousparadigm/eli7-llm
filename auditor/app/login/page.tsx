import LoginForm from "./LoginForm";

const ERROR_MESSAGES: Record<string, string> = {
  "not-authorized": "This email isn't authorized for this dashboard.",
  "missing-code": "That link is missing its access code — request a new one.",
  "invalid-link":
    "That link has expired or was already used — request a new one.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  return <LoginForm initialError={error ? ERROR_MESSAGES[error] : undefined} />;
}
