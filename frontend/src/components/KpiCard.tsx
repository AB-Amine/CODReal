type Props = {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "positive" | "negative" | "accent";
};

const toneMap = {
  default: "border-slate-200 bg-white",
  positive: "border-emerald-200 bg-emerald-50/60",
  negative: "border-rose-200 bg-rose-50/60",
  accent: "border-indigo-200 bg-indigo-50/60",
};

export function KpiCard({ label, value, hint, tone = "default" }: Props) {
  return (
    <div className={`rounded-2xl border p-4 shadow-sm ${toneMap[tone]}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
