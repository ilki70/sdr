import Link from "next/link";

type EmptyStateProps = {
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
};

export function EmptyState({ title, description, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className="rounded-[24px] border border-dashed border-white/15 bg-black/20 p-6 text-sm text-white/70">
      <p className="text-base font-semibold text-white">{title}</p>
      {description ? <p className="mt-2 max-w-2xl leading-7 text-white/60">{description}</p> : null}
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="mt-4 inline-flex rounded-full border border-[var(--accent)]/35 bg-[var(--accent)]/10 px-4 py-2 text-sm font-semibold text-[var(--accent)]"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
