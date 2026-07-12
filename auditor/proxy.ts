import type { NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

// Next.js 16 renamed Middleware to Proxy (same runtime/semantics). This is
// the auth gate: refreshes the Supabase session cookie and redirects
// unauthenticated or non-allowlisted visits to /login on every route except
// /login itself and /auth/callback (the magic-link landing route, which by
// definition runs before a session exists).
export default async function proxy(req: NextRequest) {
  return updateSession(req);
}

export const config = {
  matcher: [
    "/((?!login|auth/callback|_next/static|_next/image|favicon.ico).*)",
  ],
};
