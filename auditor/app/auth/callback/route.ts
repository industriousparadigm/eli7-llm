import { NextResponse, type NextRequest } from "next/server";
import { getPostAuthRedirect } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";

/** Magic-link landing route. Exchanges the one-time `code` query param for a
 * session, then re-checks the *authenticated* email against the allowlist --
 * mirrors the same re-check in lib/supabase/middleware.ts and
 * app/(dashboard)/layout.tsx -- before granting access. */
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");

  if (!code) {
    return NextResponse.redirect(
      new URL("/login?error=missing-code", request.url)
    );
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);

  if (error || !data.session) {
    return NextResponse.redirect(
      new URL("/login?error=invalid-link", request.url)
    );
  }

  const redirectPath = getPostAuthRedirect(data.user?.email);
  if (redirectPath !== "/conversations") {
    await supabase.auth.signOut();
  }

  return NextResponse.redirect(new URL(redirectPath, request.url));
}
