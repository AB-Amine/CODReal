type Props = {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "positive" | "negative" | "accent";
};

const toneMap = {
  default: "bg-white border-slate-200 text-slate-900 shadow",
  positive: "border-emerald-200 bg-emerald-50/60 text-slate-900 shadow-sm",
  negative: "border-rose-200 bg-rose-50/60 text-slate-900 shadow-sm",
  accent: "border-indigo-200 bg-indigo-50/60 text-slate-900 shadow-sm",
};

export function KpiCard({ label, value, hint, tone = "default" }: Props) {
  return (
    <div className={`rounded-lg border p-6 shadow ${toneMap[tone]}`}>
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
