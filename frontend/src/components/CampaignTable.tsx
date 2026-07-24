"use client";

import type { CampaignMetrics } from "@/lib/api";
import { formatMad, formatPct, formatRoas, scoreBadgeClass } from "@/lib/format";

type Props = {
  campaigns: CampaignMetrics[];
  onOpenCompass?: (campaign: CampaignMetrics) => void;
  onAnalyzeCampaign?: (campaignId: string) => void;
};

export function CampaignTable({ campaigns, onOpenCompass, onAnalyzeCampaign }: Props) {
  if (!campaigns.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        Aucune campagne à afficher. Lancez la démo ou uploadez un CSV.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Campagne</th>
              <th className="px-4 py-3 font-medium">Plateforme</th>
              <th className="px-4 py-3 font-medium">Dépense</th>
              <th className="px-4 py-3 font-medium">Livrés / Retours</th>
              <th className="px-4 py-3 font-medium">CPA réel</th>
              <th className="px-4 py-3 font-medium">ROAS réel</th>
              <th className="px-4 py-3 font-medium">Bénéfice net</th>
              <th className="px-4 py-3 font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {campaigns.map((c) => (
              <CampaignRow
                key={c.campaign_id}
                c={c}
                onOpenCompass={onOpenCompass}
                onAnalyzeCampaign={onAnalyzeCampaign}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CampaignRow({
  c,
  onOpenCompass,
  onAnalyzeCampaign,
}: {
  c: CampaignMetrics;
  onOpenCompass?: (campaign: CampaignMetrics) => void;
  onAnalyzeCampaign?: (campaignId: string) => void;
}) {
  const isHourZero = c.delivered_orders === 0;

  return (
    <tr className="hover:bg-slate-50/80">
      <td className="px-4 py-3 font-medium text-slate-900">
        <div className="flex flex-col items-start gap-1">
          <span>{c.name || c.campaign_id}</span>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {isHourZero && onOpenCompass && (
              <button
                type="button"
                onClick={() => onOpenCompass(c)}
                className="inline-flex items-center gap-1 rounded bg-indigo-50 border border-indigo-100 px-1.5 py-0.5 text-[10px] font-bold text-indigo-700 hover:bg-indigo-100 cursor-pointer"
              >
                🧭 Compass Test
              </button>
            )}
            {onAnalyzeCampaign && (
              <button
                type="button"
                onClick={() => onAnalyzeCampaign(c.campaign_id)}
                className="inline-flex items-center gap-1 rounded bg-slate-100 border border-slate-200 px-1.5 py-0.5 text-[10px] font-bold text-slate-700 hover:bg-slate-200 cursor-pointer"
              >
                📊 Analyser
              </button>
            )}
          </div>
        </div>
      </td>
      <td className="px-4 py-3 capitalize text-slate-600">{c.platform || "—"}</td>
      <td className="px-4 py-3 text-slate-700">{formatMad(c.total_spend)}</td>
      <td className="px-4 py-3 text-slate-700">
        {c.delivered_orders} / {c.returned_orders + c.refused_orders}
        {c.return_rate != null ? (
          <span className="ml-1 text-xs text-slate-400">({formatPct(c.return_rate)})</span>
        ) : null}
      </td>
      <td className="px-4 py-3 text-slate-700">{formatMad(c.real_cpa)}</td>
      <td className="px-4 py-3 font-medium text-slate-900">{formatRoas(c.real_roas)}</td>
      <td
        className={`px-4 py-3 font-medium ${
          c.net_profit < 0 ? "text-rose-600" : "text-emerald-700"
        }`}
      >
        {formatMad(c.net_profit)}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${scoreBadgeClass(
            c.performance_score
          )}`}
        >
          {c.performance_label || c.performance_score}
        </span>
      </td>
    </tr>
  );
}
