import Link from "next/link";
import { BRAND_NAME } from "@/lib/brand";
import { CommandBar } from "@/components/layout/command-bar";
import { SidebarNav } from "@/components/layout/sidebar-nav";

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
          <SidebarNav />
        </aside>
        <section className="space-y-6">
          <CommandBar />
          {children}
        </section>
      </div>
    </div>
  );
}
