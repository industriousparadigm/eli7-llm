"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth-actions";

const LINKS = [
  { href: "/conversations", label: "Conversations" },
  { href: "/memory", label: "O que a Nuvem sabe" },
  { href: "/curator", label: "Curator timeline" },
  { href: "/health", label: "Health" },
];

export default function Nav({ userEmail }: { userEmail?: string }) {
  const pathname = usePathname();

  return (
    <nav className="app-nav">
      <div className="app-nav-brand">
        <strong>Eli7 Auditor</strong>
        <span>DianasNuvem</span>
      </div>
      <div className="app-nav-links">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="app-nav-link"
            data-active={pathname?.startsWith(link.href)}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <div className="app-nav-footer">
        {userEmail && <div className="app-nav-user">{userEmail}</div>}
        <form action={logout}>
          <button type="submit">Log out</button>
        </form>
      </div>
    </nav>
  );
}
