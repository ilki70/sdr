import Link from "next/link";

const shortcuts = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/agent-lab", label: "Agent Lab" },
  { href: "/quality", label: "Quality" },
];

export function CommandBar() {
  return (
    <div className="rounded-[24px] border border-white/10 bg-black/20 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.24em] text-white/40">Atalhos</p>
          <p className="mt-1 text-sm text-white/70">Acessos rapidos para operar o studio sem ficar pulando menus.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {shortcuts.map((shortcut) => (
            <Link
              key={shortcut.href}
              href={shortcut.href}
              className="rounded-full border border-white/12 bg-white/5 px-4 py-2 text-sm text-white/85 transition hover:border-white/20 hover:bg-white/10"
            >
              {shortcut.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
