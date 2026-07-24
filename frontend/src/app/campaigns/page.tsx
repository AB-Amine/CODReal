"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { CampaignTable } from "@/components/CampaignTable";
import {
  fetchDashboard,
  listCampaigns,
  runPipeline,
  type CampaignMetrics,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { DEMO_PIPELINE } from "@/lib/demo-data";
import { formatMad } from "@/lib/format";

export default function CampaignsPage() {
  const { user, accessToken } = useAuth();
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<CampaignMetrics[]>([]);
  const [raw, setRaw] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user && accessToken) {
      Promise.all([fetchDashboard(accessToken), listCampaigns(accessToken)])
        .then(([dash, list]) => {
          setCampaigns(dash.kpis.campaigns);
          setRaw(list.campaigns);
        })
        .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
    } else {
      runPipeline(DEMO_PIPELINE)
        .then((d) => setCampaigns(d.kpis.campaigns))
        .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
    }
  }, [user, accessToken]);

  const handleAnalyzeCampaign = (campaignId: string) => {
    router.push(`/dashboard?campaign_id=${encodeURIComponent(campaignId)}`);
  };

  return (
    <AppShell title="Campagnes">
      {error ? <p className="mb-4 text-sm text-rose-600">{error}</p> : null}
      <p className="mb-4 text-sm text-slate-500">
        {user
          ? "Données utilisateur (tri bénéfice net croissant)."
          : "Mode démo locale — connectez-vous pour vos campagnes."}
      </p>
      <CampaignTable campaigns={campaigns} onAnalyzeCampaign={handleAnalyzeCampaign} />

      {raw.length > 0 ? (
        <section className="mt-8">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Enregistrements DB
          </h2>
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Nom</th>
                  <th className="px-4 py-3">Plateforme</th>
                  <th className="px-4 py-3">Dépense stockée</th>
                  <th className="px-4 py-3">ID externe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {raw.map((c) => (
                  <tr key={String(c.id)}>
                    <td className="px-4 py-3 font-medium">{String(c.name ?? "—")}</td>
                    <td className="px-4 py-3 capitalize">{String(c.platform ?? "—")}</td>
                    <td className="px-4 py-3">{formatMad(Number(c.spend ?? 0))}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">
                      {String(c.platform_campaign_id ?? "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </AppShell>
  );
}
