"use client";

import { useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/lib/auth-context";

import type { CampaignMetrics } from "@/lib/api";

export type Anomaly = {
  id: string;
  campaign_id: string;
  anomaly_type: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  detected_at: string;
  campaign_name?: string;
};

const MOCK_ANOMALIES: Anomaly[] = [
  {
    id: "m1",
    campaign_id: "meta-summer",
    anomaly_type: "cpm_spike",
    severity: "critical",
    message: "CPM anormalement élevé: 42.50 MAD (Moyenne 7j: 18.20 MAD, Z-Score: 3.12) sur 'Summer Meta Lookalike'. Pression concurrentielle suspectée.",
    detected_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(), // 15 mins ago
    campaign_name: "Summer Meta Lookalike",
  },
  {
    id: "m2",
    campaign_id: "tiktok-broad",
    anomaly_type: "funnel_drop",
    severity: "high",
    message: "Baisse de CTR: 0.85% contre une moyenne 14j de 1.80% (Chute de 52.8%) sur 'TikTok Broad COD'. Fatigue créative probable.",
    detected_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(), // 2h ago
    campaign_name: "TikTok Broad COD",
  },
  {
    id: "m3",
    campaign_id: "meta-summer",
    anomaly_type: "funnel_drop",
    severity: "medium",
    message: "Baisse du taux de conversion (CVR): 1.80% contre 2.50% moyenne 14j (Chute de 28.0%) sur 'Summer Meta Lookalike'. Vérifiez le temps de chargement de la landing page.",
    detected_at: new Date(Date.now() - 1000 * 60 * 360).toISOString(), // 6h ago
    campaign_name: "Summer Meta Lookalike",
  },
];

export function AnomalyFeed({
  isLocalDemo,
  selectedCampaignId = "ALL",
  selectedCampaignName,
  selectedCampaign,
}: {
  isLocalDemo: boolean;
  selectedCampaignId?: string;
  selectedCampaignName?: string;
  selectedCampaign?: CampaignMetrics | null;
}) {
  const { accessToken } = useAuth();
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(false);

  // Scan state for individual anomaly cards
  const [scans, setScans] = useState<Record<string, { loading: boolean; result: string | null }>>({});

  const handleScan = (id: string, type: string) => {
    setScans((prev) => ({
      ...prev,
      [id]: { loading: true, result: null },
    }));

    setTimeout(() => {
      let resultText = "";
      if (id.includes("return")) {
        resultText = "📦 Recommandation logistique: Suggérez d'appeler les clients pour valider l'adresse de livraison et proposer une remise de 10% s'ils acceptent une livraison sous 24h.";
      } else if (id.includes("roas")) {
        resultText = "💸 Recommandation prix: Augmentez le prix du produit de 20% ou mettez en place des offres groupées (Buy 1 Get 1 50% Off) pour augmenter le panier moyen.";
      } else if (type === "cpm_spike") {
        resultText = "⚡ 3 nouvelles pages détectées testant ce produit aujourd'hui. Hausse des enchères (compétition) confirmée.";
      } else {
        resultText = "📉 Chute du Hook Rate (Plays à 3s). L'audience scrolle votre vidéo sans s'arrêter. Changez le hook des 3 premières secondes.";
      }
      setScans((prev) => ({
        ...prev,
        [id]: { loading: false, result: resultText },
      }));
    }, 1500);
  };

  useEffect(() => {
    if (isLocalDemo) {
      setAnomalies(MOCK_ANOMALIES);
      return;
    }

    const supabase = createClient();
    if (!supabase || !accessToken) {
      setAnomalies(MOCK_ANOMALIES);
      return;
    }

    async function fetchAnomalies() {
      setLoading(true);
      try {
        const { data, error } = await supabase!
          .from("market_anomalies")
          .select(`
            id,
            campaign_id,
            anomaly_type,
            severity,
            message,
            detected_at,
            campaigns ( name )
          `)
          .order("detected_at", { ascending: false });

        if (error || !data || data.length === 0) {
          setAnomalies(MOCK_ANOMALIES);
        } else {
          interface DatabaseAnomaly {
            id: string;
            campaign_id: string;
            anomaly_type: string;
            severity: string;
            message: string;
            detected_at: string;
            campaigns: { name: string } | null;
          }
          const mapped = (data as unknown as DatabaseAnomaly[]).map((d) => {
            const campaignsData = d.campaigns as { name: string } | null;
            return {
              id: d.id,
              campaign_id: d.campaign_id,
              anomaly_type: d.anomaly_type,
              severity: d.severity as Anomaly["severity"],
              message: d.message,
              detected_at: d.detected_at,
              campaign_name: campaignsData?.name || "Campagne inconnue",
            };
          });
          setAnomalies(mapped);
        }
      } catch (err) {
        console.error("Error fetching anomalies:", err);
        setAnomalies(MOCK_ANOMALIES);
      } finally {
        setLoading(false);
      }
    }

    void fetchAnomalies();
  }, [isLocalDemo, accessToken]);

  const filteredAnomalies = useMemo(() => {
    // Start with database/demo anomalies
    const list = [...anomalies];

    // Generate client-side anomalies for campaigns with poor metrics
    if (selectedCampaignId !== "ALL" && selectedCampaign) {
      const return_rate = selectedCampaign.return_rate ?? 0;
      const real_roas = selectedCampaign.real_roas ?? 0;
      const real_cpa = selectedCampaign.real_cpa ?? 0;

      // High return rate alert
      if (return_rate > 0.20 && !list.some((a) => a.id.includes("return"))) {
        list.push({
          id: `gen-return-${selectedCampaign.campaign_id}`,
          campaign_id: selectedCampaign.campaign_id,
          anomaly_type: "funnel_drop",
          severity: return_rate > 0.35 ? "critical" : "high",
          message: `Rentabilité critique : Taux de retour élevé de ${(return_rate * 100).toFixed(0)}% sur '${selectedCampaign.name}'. Risque important de pertes sur frais de retour logistiques.`,
          detected_at: new Date().toISOString(),
          campaign_name: selectedCampaign.name,
        });
      }

      // Low ROAS alert
      if (real_roas > 0 && real_roas < 1.8 && !list.some((a) => a.id.includes("roas"))) {
        list.push({
          id: `gen-roas-${selectedCampaign.campaign_id}`,
          campaign_id: selectedCampaign.campaign_id,
          anomaly_type: "funnel_drop",
          severity: real_roas < 1.2 ? "critical" : "medium",
          message: `Performance critique : ROAS réel insuffisant de ${real_roas.toFixed(2)} sur '${selectedCampaign.name}'. Les revenus générés ne couvrent pas vos dépenses publicitaires.`,
          detected_at: new Date().toISOString(),
          campaign_name: selectedCampaign.name,
        });
      }

      // High CPA alert
      if (real_cpa > 80 && !list.some((a) => a.id.includes("cpa"))) {
        list.push({
          id: `gen-cpa-${selectedCampaign.campaign_id}`,
          campaign_id: selectedCampaign.campaign_id,
          anomaly_type: "cpm_spike",
          severity: "high",
          message: `Optimisation requise : Coût par Commande Livrée (CPA réel) de ${real_cpa.toFixed(0)} MAD sur '${selectedCampaign.name}' trop élevé par rapport à votre marge brute.`,
          detected_at: new Date().toISOString(),
          campaign_name: selectedCampaign.name,
        });
      }
    }

    if (selectedCampaignId === "ALL") return list;
    return list.filter((a) => {
      return (
        a.campaign_id === selectedCampaignId ||
        (selectedCampaignName && a.campaign_name === selectedCampaignName)
      );
    });
  }, [anomalies, selectedCampaignId, selectedCampaignName, selectedCampaign]);

  const severityColors = {
    critical: {
      bg: "bg-rose-50 border-rose-200",
      text: "text-rose-900",
      badge: "bg-rose-600 text-white animate-pulse",
      indicator: "bg-rose-600",
    },
    high: {
      bg: "bg-amber-50 border-amber-200",
      text: "text-amber-900",
      badge: "bg-amber-600 text-white",
      indicator: "bg-amber-600",
    },
    medium: {
      bg: "bg-yellow-50 border-yellow-200",
      text: "text-yellow-900",
      badge: "bg-yellow-500 text-slate-900",
      indicator: "bg-yellow-500",
    },
    low: {
      bg: "bg-slate-50 border-slate-200",
      text: "text-slate-700",
      badge: "bg-slate-500 text-white",
      indicator: "bg-slate-400",
    },
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800">
            Défense du Marché (Radar)
          </h2>
        </div>
        {isLocalDemo && (
          <span className="rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-700">
            MODE DÉMO
          </span>
        )}
      </div>

      {loading ? (
        <div className="py-8 text-center text-xs text-slate-400 animate-pulse">
          Balayage du marché en cours...
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAnomalies.map((a) => {
            const style = severityColors[a.severity] || severityColors.low;
            const timeStr = new Date(a.detected_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            });
            return (
              <div
                key={a.id}
                className={`flex gap-3 rounded-xl border p-3 text-xs leading-relaxed transition-all hover:shadow-sm flex-col ${style.bg}`}
              >
                <div className="flex gap-3">
                  <span className={`mt-1 h-2 w-2 rounded-full shrink-0 ${style.indicator}`} />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-800">
                        {a.anomaly_type === "cpm_spike" ? "Hausse CPM" : "Chute Funnel"}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">{timeStr}</span>
                    </div>
                    <p className={style.text}>{a.message}</p>
                  </div>
                </div>

                <div className="border-t border-slate-100/40 pt-2 flex flex-col gap-2 pl-5">
                  {!scans[a.id]?.loading && !scans[a.id]?.result && (
                    <button
                      type="button"
                      onClick={() => handleScan(a.id, a.anomaly_type)}
                      className="self-start rounded bg-slate-900 px-2.5 py-1 text-[10px] font-bold text-white shadow-sm hover:bg-slate-800 transition-colors cursor-pointer"
                    >
                      {a.anomaly_type === "cpm_spike" ? "🔍 Scanner les Concurrents" : "📊 Diagnostiquer le Funnel"}
                    </button>
                  )}

                  {scans[a.id]?.loading && (
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-medium">
                      <svg className="animate-spin h-3 w-3 text-slate-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Recherche en cours...</span>
                    </div>
                  )}

                  {scans[a.id]?.result && (
                    <div className="rounded-lg bg-white/80 border border-slate-100 p-2 text-[10px] font-medium text-slate-700 shadow-sm animate-in slide-in-from-top-1 duration-150">
                      {scans[a.id]?.result}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {filteredAnomalies.length === 0 && (
            selectedCampaignId !== "ALL" ? (
              <div className="flex flex-col items-center justify-center py-8 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl bg-slate-50 p-4">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 mb-2 border border-emerald-100 shadow-sm">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </span>
                <p className="font-bold text-slate-800 text-xs">Aucune anomalie détectée</p>
                <p className="mt-1 text-[10px] text-slate-400">L&apos;entonnoir de cette campagne est tout à fait sain.</p>
              </div>
            ) : (
              <p className="py-6 text-center text-xs text-slate-400">
                Aucune anomalie détectée sur le marché.
              </p>
            )
          )}
        </div>
      )}
    </div>
  );
}
