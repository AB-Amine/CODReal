"use client";

import { useCallback, useEffect, useMemo, useState, Suspense } from "react";
import { AlertsList } from "@/components/AlertsList";
import { AppShell } from "@/components/AppShell";
import { CampaignTable } from "@/components/CampaignTable";
import { KpiCard } from "@/components/KpiCard";
import { AnomalyFeed } from "./components/AnomalyFeed";
import {
  fetchDashboard,
  healthCheck,
  runBuiltInDemo,
  runPipeline,
  seedDemo,
  type AlertItem,
  type DashboardKPIs,
  type PipelineResponse,
  type CampaignMetrics,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { DEMO_PIPELINE } from "@/lib/demo-data";
import { formatMad, formatPct, formatRoas } from "@/lib/format";
import { useSearchParams } from "next/navigation";

function DashboardContent() {
  const { user, accessToken, configured } = useAuth();
  const searchParams = useSearchParams();
  const campaignIdParam = searchParams.get("campaign_id");
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [matchStats, setMatchStats] = useState<PipelineResponse["matching"]["stats"] | null>(
    null
  );
  const [meta, setMeta] = useState<{ orders?: number; matches?: number } | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"local" | "db">("local");

  // Filter States
  const [days, setDays] = useState<number>(7);
  const [platform, setPlatform] = useState<string>("all");
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("ALL");

  useEffect(() => {
    if (campaignIdParam) {
      setSelectedCampaignId(campaignIdParam);
    }
  }, [campaignIdParam]);

  // Recalculated KPIs based on selectedCampaignId
  const computedKpis = useMemo(() => {
    if (!kpis) return null;
    if (selectedCampaignId === "ALL") {
      return {
        total_ad_spend: kpis.total_ad_spend,
        delivered_revenue: kpis.delivered_revenue,
        net_profit: kpis.net_profit,
        real_roas: kpis.real_roas,
        global_return_rate: kpis.global_return_rate,
        total_returned: kpis.total_returned,
        total_delivered: kpis.total_delivered,
      };
    }

    const campaign = kpis.campaigns.find((c) => c.campaign_id === selectedCampaignId);
    if (!campaign) {
      return {
        total_ad_spend: 0,
        delivered_revenue: 0,
        net_profit: 0,
        real_roas: null,
        global_return_rate: null,
        total_returned: 0,
        total_delivered: 0,
      };
    }

    const total_returned = campaign.returned_orders + campaign.refused_orders;
    return {
      total_ad_spend: campaign.total_spend,
      delivered_revenue: campaign.net_revenue,
      net_profit: campaign.net_profit,
      real_roas: campaign.real_roas,
      global_return_rate: campaign.return_rate,
      total_returned: total_returned,
      total_delivered: campaign.delivered_orders,
    };
  }, [kpis, selectedCampaignId]);

  const filteredCampaigns = useMemo(() => {
    if (!kpis) return [];
    if (selectedCampaignId === "ALL") return kpis.campaigns;
    return kpis.campaigns.filter((c) => c.campaign_id === selectedCampaignId);
  }, [kpis, selectedCampaignId]);

  const selectedCampaignName = useMemo(() => {
    if (selectedCampaignId === "ALL") return null;
    const campaign = kpis?.campaigns.find((c) => c.campaign_id === selectedCampaignId);
    return campaign ? campaign.name : null;
  }, [kpis, selectedCampaignId]);

  const selectedCampaignMetrics = useMemo(() => {
    if (selectedCampaignId === "ALL") return null;
    return kpis?.campaigns.find((c) => c.campaign_id === selectedCampaignId) || null;
  }, [kpis, selectedCampaignId]);

  const filteredAlerts = useMemo(() => {
    if (selectedCampaignId === "ALL") return alerts;
    return alerts.filter((a) => {
      return (
        a.campaign_id === selectedCampaignId ||
        (selectedCampaignName && a.name === selectedCampaignName)
      );
    });
  }, [alerts, selectedCampaignId, selectedCampaignName]);

  // Hour Zero Compass Modal States
  const [isCompassModalOpen, setIsCompassModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<CampaignMetrics | null>(null);
  const [isResearching, setIsResearching] = useState(false);
  const [productName, setProductName] = useState("");
  const [sellingPrice, setSellingPrice] = useState<number>(250);
  const [breakEvenMargin, setBreakEvenMargin] = useState<number>(150);
  const [compassResults, setCompassResults] = useState<{
    targetCpa: number;
    requiredCtr: number;
    expectedCpm: number;
    targetCpc: number;
  } | null>(null);

  const handleOpenCompass = (campaign: CampaignMetrics) => {
    setSelectedCampaign(campaign);
    setProductName(campaign.name || "");
    setSellingPrice(250);
    setBreakEvenMargin(150);
    setCompassResults(null);
    setIsResearching(false);
    setIsCompassModalOpen(true);
  };

  const handleLaunchResearch = (e: React.FormEvent) => {
    e.preventDefault();
    setIsResearching(true);
    setCompassResults(null);
    setTimeout(() => {
      const nameLower = productName.toLowerCase();
      let expectedCpm = 25; // Default CPM (MAD)
      let expectedCvr = 0.03; // Default CVR (3%)

      // Custom category adjustments based on Moroccan/GCC COD benchmarks
      if (
        nameLower.includes("cosmetique") ||
        nameLower.includes("creme") ||
        nameLower.includes("peau") ||
        nameLower.includes("parfum") ||
        nameLower.includes("beauty") ||
        nameLower.includes("cheveux")
      ) {
        expectedCpm = 45; // High competition in beauty
        expectedCvr = 0.025; // 2.5%
      } else if (
        nameLower.includes("vetement") ||
        nameLower.includes("robe") ||
        nameLower.includes("mode") ||
        nameLower.includes("chaussure") ||
        nameLower.includes("sac") ||
        nameLower.includes("fashion")
      ) {
        expectedCpm = 30; // Medium-high competition
        expectedCvr = 0.035; // 3.5%
      } else if (
        nameLower.includes("cuisine") ||
        nameLower.includes("robot") ||
        nameLower.includes("mixeur") ||
        nameLower.includes("gadget") ||
        nameLower.includes("maison") ||
        nameLower.includes("outil")
      ) {
        expectedCpm = 18; // Low/broad CPM for utility gadgets
        expectedCvr = 0.04; // 4.0%
      } else if (
        nameLower.includes("enfant") ||
        nameLower.includes("jouet") ||
        nameLower.includes("bebe") ||
        nameLower.includes("baby")
      ) {
        expectedCpm = 22;
        expectedCvr = 0.03;
      }

      const targetCpa = breakEvenMargin * 0.7; // Target CPA is 70% of Break-Even
      const targetCpc = targetCpa * expectedCvr;
      const requiredCtr = targetCpc > 0 ? (expectedCpm / 1000.0) / targetCpc : 0;
      
      setCompassResults({
        targetCpa,
        requiredCtr,
        expectedCpm,
        targetCpc,
      });
      setIsResearching(false);
    }, 2000);
  };

  useEffect(() => {
    healthCheck()
      .then(() => setApiOk(true))
      .catch(() => setApiOk(false));
  }, []);

  const loadLocalDemo = useCallback(async () => {
    setLoading(true);
    setError(null);
    setMode("local");
    try {
      // Prefer built-in demo endpoint; fall back to pipeline payload
      let data: PipelineResponse;
      try {
        data = await runBuiltInDemo();
      } catch {
        data = await runPipeline(DEMO_PIPELINE);
      }
      setKpis(data.kpis);
      setAlerts(data.alerts);
      setMatchStats(data.matching.stats);
      setMeta(null);
      setSelectedCampaignId("ALL");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "API injoignable. Lancez le backend sur le port 8000."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFromDb = useCallback(async (currentDays?: number, currentPlatform?: string) => {
    if (!accessToken) {
      setError("Connectez-vous pour charger vos données Supabase.");
      return;
    }
    setLoading(true);
    setError(null);
    setMode("db");
    try {
      const data = await fetchDashboard(accessToken, currentDays, currentPlatform);
      setKpis(data.kpis);
      setAlerts(data.alerts);
      setMatchStats(null);
      setMeta({ orders: data.orders_count, matches: data.matches_count });
      setSelectedCampaignId("ALL");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur chargement DB");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  const runSeedDemo = useCallback(async () => {
    if (!accessToken) {
      setError("Connectez-vous pour seed la démo en base.");
      return;
    }
    setLoading(true);
    setError(null);
    setMode("db");
    try {
      const data = await seedDemo(accessToken);
      setKpis(data.kpis);
      setAlerts(data.alerts);
      setMatchStats(data.matching?.stats ?? null);
      setMeta({
        orders: data.orders_saved,
        matches: data.matches_saved,
      });
      setSelectedCampaignId("ALL");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur seed");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (apiOk) {
      if (user) {
        setMode("db");
      } else {
        setMode("local");
        void loadLocalDemo();
      }
    }
  }, [apiOk, user, loadLocalDemo]);

  useEffect(() => {
    if (apiOk && user && accessToken && mode === "db") {
      void loadFromDb(days, platform === "all" ? undefined : platform);
    }
  }, [apiOk, user, accessToken, mode, days, platform, loadFromDb]);



  return (
    <AppShell title="Tableau de bord">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1 text-sm text-slate-500">
          <p>
            API:{" "}
            {apiOk === null ? (
              <span>vérification…</span>
            ) : apiOk ? (
              <span className="font-medium text-emerald-600">connectée</span>
            ) : (
              <span className="font-medium text-rose-600">hors ligne</span>
            )}
            {" · "}
            Mode:{" "}
            <span className="font-medium text-slate-700">
              {mode === "db" ? "base utilisateur" : "démo locale"}
            </span>
            {user ? (
              <span className="ml-1 text-emerald-700">· connecté</span>
            ) : (
              <span className="ml-1">· anonyme</span>
            )}
          </p>
          {!configured ? (
            <p className="text-xs text-amber-700">
              Supabase frontend non configuré — démo locale uniquement. Voir docs/SUPABASE_SETUP.md
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadLocalDemo()}
            disabled={loading || apiOk === false}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            Démo locale
          </button>
          {user ? (
            <>
              <button
                type="button"
                onClick={() => void loadFromDb(days, platform === "all" ? undefined : platform)}
                disabled={loading}
                className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-800 hover:bg-indigo-100 disabled:opacity-50"
              >
                Mes données
              </button>
              <button
                type="button"
                onClick={() => void runSeedDemo()}
                disabled={loading}
                className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
              >
                {loading ? "…" : "Charger démo (DB)"}
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => void loadLocalDemo()}
              disabled={loading || apiOk === false}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? "Calcul…" : "Rafraîchir démo"}
            </button>
          )}
        </div>
      </div>

      {error ? (
        <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
          <p className="mt-1 text-xs opacity-80">
            Backend: uvicorn · Supabase: docs/SUPABASE_SETUP.md
          </p>
        </div>
      ) : null}

      {/* Filter controls */}
      <div className="mb-6 flex flex-wrap gap-4 items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-2">
          <label htmlFor="date-filter" className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Période :
          </label>
          <select
            id="date-filter"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 outline-none focus:border-indigo-500"
          >
            <option value={1}>Aujourd&apos;hui</option>
            <option value={2}>Hier</option>
            <option value={7}>7 derniers jours</option>
            <option value={30}>30 derniers jours</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="platform-filter" className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Plateforme :
          </label>
          <select
            id="platform-filter"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 outline-none focus:border-indigo-500"
          >
            <option value="all">Toutes les plateformes</option>
            <option value="meta">Meta (Facebook)</option>
            <option value="tiktok">TikTok</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="campaign-filter" className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Campagne :
          </label>
          <select
            id="campaign-filter"
            value={selectedCampaignId}
            onChange={(e) => setSelectedCampaignId(e.target.value)}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 outline-none focus:border-indigo-500"
          >
            <option value="ALL">Toutes les campagnes</option>
            {kpis?.campaigns.map((c) => (
              <option key={c.campaign_id} value={c.campaign_id}>
                {c.name || c.campaign_id}
              </option>
            ))}
          </select>
        </div>
        
        {loading && (
          <span className="text-xs text-indigo-600 font-medium animate-pulse ml-auto">
            Chargement des filtres...
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <KpiCard label="Dépense pub" value={formatMad(computedKpis?.total_ad_spend)} hint="Meta + TikTok" />
        <KpiCard
          label="CA livré"
          value={formatMad(computedKpis?.delivered_revenue)}
          hint="Montants collectés"
          tone="accent"
        />
        <KpiCard
          label="Bénéfice net"
          value={formatMad(computedKpis?.net_profit)}
          hint="Après pub + frais retours"
          tone={computedKpis == null ? "default" : computedKpis.net_profit >= 0 ? "positive" : "negative"}
        />
        <KpiCard
          label="ROAS réel"
          value={formatRoas(computedKpis?.real_roas)}
          hint="Revenu livré / dépense"
        />
        <KpiCard
          label="Taux de retour"
          value={formatPct(computedKpis?.global_return_rate)}
          hint={`${computedKpis?.total_returned ?? 0} retours / refus`}
        />
      </div>

      {matchStats ? (
        <p className="mt-4 text-xs text-slate-500">
          Matching: {matchStats.matched}/{matchStats.total_orders} commandes (
          {(matchStats.match_rate * 100).toFixed(0)}%)
        </p>
      ) : null}
      {meta ? (
        <p className="mt-2 text-xs text-slate-500">
          DB: {meta.orders ?? "—"} commandes · {meta.matches ?? "—"} matchs
        </p>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Campagnes
            </h2>
            <CampaignTable
              campaigns={filteredCampaigns}
              onOpenCompass={handleOpenCompass}
              onAnalyzeCampaign={setSelectedCampaignId}
            />
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Alertes
            </h2>
            <AlertsList alerts={filteredAlerts} />
          </section>
        </div>

        <div className="space-y-6">
          <AnomalyFeed
            isLocalDemo={mode === "local"}
            selectedCampaignId={selectedCampaignId}
            selectedCampaignName={selectedCampaignName || undefined}
            selectedCampaign={selectedCampaignMetrics}
          />
        </div>
      </div>

      {isCompassModalOpen && selectedCampaign && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            onClick={() => setIsCompassModalOpen(false)}
          ></div>

          <div className="relative w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-150">
            <button
              type="button"
              className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 cursor-pointer"
              onClick={() => setIsCompassModalOpen(false)}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <div className="mb-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                🧭 Compass Hour Zero — {selectedCampaign.name || selectedCampaign.campaign_id}
              </h3>
              <p className="text-xs text-slate-500">
                Générez les cibles d&apos;acquisition minimales pour lancer votre produit sur le marché.
              </p>
            </div>

            <form onSubmit={handleLaunchResearch} className="space-y-4">
              <div>
                <label htmlFor="product-name-input" className="block text-xs font-semibold text-slate-700 mb-1">
                  Nom du Produit
                </label>
                <input
                  id="product-name-input"
                  type="text"
                  required
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="Ex: Robot Mixeur Cuisine"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
                  disabled={isResearching}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="selling-price-input" className="block text-xs font-semibold text-slate-700 mb-1">
                    Prix de Vente (MAD)
                  </label>
                  <input
                    id="selling-price-input"
                    type="number"
                    required
                    min="1"
                    value={sellingPrice}
                    onChange={(e) => setSellingPrice(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
                    disabled={isResearching}
                  />
                </div>
                <div>
                  <label htmlFor="break-even-input" className="block text-xs font-semibold text-slate-700 mb-1">
                    Marge de Sécurité / Break-Even (MAD)
                  </label>
                  <input
                    id="break-even-input"
                    type="number"
                    required
                    min="1"
                    value={breakEvenMargin}
                    onChange={(e) => setBreakEvenMargin(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-indigo-500"
                    disabled={isResearching}
                  />
                </div>
              </div>

              {!compassResults && !isResearching && (
                <button
                  type="submit"
                  className="w-full rounded-lg bg-indigo-600 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-indigo-500 transition-colors cursor-pointer"
                >
                  🚀 Lancer la recherche marché
                </button>
              )}
            </form>

            {isResearching && (
              <div className="mt-6 flex flex-col items-center justify-center py-6 text-center">
                <span className="relative flex h-10 w-10">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-10 w-10 bg-indigo-600 items-center justify-center">
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </span>
                </span>
                <p className="mt-3 text-xs text-indigo-700 font-semibold animate-pulse">
                  Analyse de la Meta Ad Library en cours...
                </p>
                <p className="mt-1 text-[10px] text-slate-400">
                  Extraction des volumes et des CPC concurrentiels sur le marché marocain
                </p>
              </div>
            )}

            {compassResults && (
              <div className="mt-6 border-t border-slate-100 pt-5 space-y-4">
                <div className="rounded-xl bg-indigo-50/50 border border-indigo-100 p-4">
                  <h4 className="text-xs font-bold text-indigo-900 mb-2 uppercase tracking-wide">
                    Résultats de la Simulation
                  </h4>
                  <div className="grid gap-3 sm:grid-cols-2 text-xs">
                    <div className="bg-white rounded-lg p-3 border border-slate-100">
                      <p className="text-slate-400 font-medium">CPA Max Recommandé (70%):</p>
                      <p className="text-base font-extrabold text-slate-900 mt-0.5">{compassResults.targetCpa.toFixed(0)} MAD</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-slate-100">
                      <p className="text-slate-400 font-medium">CVR Cible Minimum:</p>
                      <p className="text-base font-extrabold text-slate-900 mt-0.5">3.00%</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-slate-100">
                      <p className="text-slate-400 font-medium">CPC Cible Maximum:</p>
                      <p className="text-base font-extrabold text-slate-900 mt-0.5">{compassResults.targetCpc.toFixed(2)} MAD</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-slate-100">
                      <p className="text-slate-400 font-medium">CTR Requis minimum:</p>
                      <p className="text-base font-extrabold text-slate-900 mt-0.5">{(compassResults.requiredCtr * 100).toFixed(2)}%</p>
                    </div>
                  </div>
                  <p className="mt-3 text-[10px] text-slate-400 text-center">
                    Cible calculée pour un CPM moyen simulé de {compassResults.expectedCpm} MAD
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleLaunchResearch}
                    className="flex-1 rounded-lg border border-slate-200 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
                  >
                    Relancer
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsCompassModalOpen(false)}
                    className="flex-1 rounded-lg bg-slate-900 py-2 text-xs font-semibold text-white hover:bg-slate-800 cursor-pointer"
                  >
                    Fermer
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <AppShell title="Tableau de bord">
        <div className="py-8 text-center text-xs text-slate-400 animate-pulse">
          Chargement du tableau de bord...
        </div>
      </AppShell>
    }>
      <DashboardContent />
    </Suspense>
  );
}
