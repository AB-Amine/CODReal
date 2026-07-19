export function formatMad(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fr-MA", {
    style: "currency",
    currency: "MAD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatRoas(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(2)}x`;
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function scoreBadgeClass(score: string): string {
  switch (score) {
    case "excellent":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "good":
      return "bg-sky-100 text-sky-800 border-sky-200";
    case "warning":
      return "bg-amber-100 text-amber-900 border-amber-200";
    case "critical":
      return "bg-rose-100 text-rose-800 border-rose-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}
