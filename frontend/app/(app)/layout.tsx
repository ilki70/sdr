import Link from "next/link";
import { BRAND_NAME } from "@/lib/brand";

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
  { href: "/commissions", label: "Commissions" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
          <strong>{BRAND_NAME}</strong>
          <form action="/api/auth/logout" method="post">
            <button className="rounded-md border border-white/20 px-3 py-1 text-sm" type="submit">
              Sair
            </button>
          </form>
        </div>
      </header>
      <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-6 px-6 py-6 lg:grid-cols-[220px_1fr]">
        <aside className="rounded-lg border border-white/10 bg-white/5 p-4">
          <nav className="flex flex-col gap-2">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-md px-3 py-2 text-sm hover:bg-white/10">
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <section>{children}</section>
      </div>
    </div>
  );
}
