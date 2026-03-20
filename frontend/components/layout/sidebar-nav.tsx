"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/agents", label: "Agents" },
  { href: "/clients", label: "Clients" },
  { href: "/products", label: "Products" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/personas", label: "Personas" },
  { href: "/integrations", label: "Integrations" },
  { href: "/conversations", label: "Conversations" },
  { href: "/quality", label: "Quality" },
  { href: "/agent-lab", label: "Agent Lab" },
  { href: "/sales", label: "Sales" },
  { href: "/commissions", label: "Commissions" },
  { href: "/settings", label: "Settings" },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-2">
      {navItems.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`rounded-[14px] px-3 py-2 text-sm transition ${
              active
                ? "border border-[var(--accent)]/30 bg-[var(--accent)]/12 text-white"
                : "text-white/78 hover:bg-white/10 hover:text-white"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
