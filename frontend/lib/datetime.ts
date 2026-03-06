export const SAO_PAULO_TIMEZONE = "America/Sao_Paulo";

export function formatDateTimeSP(value: string | null): string {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: SAO_PAULO_TIMEZONE,
  }).format(new Date(value));
}

export function formatDateSP(value: string | null): string {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeZone: SAO_PAULO_TIMEZONE,
  }).format(new Date(value));
}

export function formatMoneyBRL(value: number | string | null | undefined): string {
  const amount = typeof value === "string" ? Number(value) : value ?? 0;
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number.isFinite(amount) ? amount : 0);
}
