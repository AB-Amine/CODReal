import type { AlertItem } from "@/lib/api";

const severityClass: Record<string, string> = {
  critical: "border-rose-200 bg-rose-50 text-rose-900",
  warning: "border-amber-200 bg-amber-50 text-amber-950",
  info: "border-sky-200 bg-sky-50 text-sky-900",
};

export function AlertsList({ alerts }: { alerts: AlertItem[] }) {
  if (!alerts.length) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4 text-sm text-emerald-800">
        Aucune alerte — toutes les campagnes respectent les seuils de base.
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {alerts.map((a, i) => (
        <li
          key={`${a.campaign_id}-${a.code}-${i}`}
          className={`rounded-xl border px-4 py-3 text-sm ${severityClass[a.severity] || severityClass.info}`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-white/70 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide">
              {a.severity}
            </span>
            <span className="font-medium">{a.name}</span>
            <span className="text-xs opacity-70">{a.code}</span>
          </div>
          <p className="mt-1">{a.message}</p>
        </li>
      ))}
    </ul>
  );
}
