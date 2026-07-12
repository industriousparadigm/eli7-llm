import { redirect } from "next/navigation";
import Nav from "@/components/Nav";
import { isEmailAllowed } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Authoritative recheck (network-verified, not just the cookie) so a
  // stale or forged session can never reach the data, even if the proxy
  // gate were somehow bypassed.
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!isEmailAllowed(user?.email)) {
    redirect("/login");
  }

  return (
    <div className="app-shell">
      <Nav userEmail={user?.email ?? undefined} />
      <main className="app-main">{children}</main>
    </div>
  );
}
