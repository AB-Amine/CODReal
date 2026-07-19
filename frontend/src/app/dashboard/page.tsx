"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertsList } from "@/components/AlertsList";
import { AppShell } from "@/components/AppShell";
import { CampaignTable } from "@/components/CampaignTable";
import { KpiCard } from "@/components/KpiCard";
import {
  fetchDashboard,
  healthCheck,
  runBuiltInDemo,
  runPipeline,
  seedDemo,
  type AlertItem,
  type DashboardKPIs,
  type PipelineResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { DEMO_PIPELINE } from "@/lib/demo-data";
import { formatMad, formatPct, formatRoas } from "@/lib/format";

export default function DashboardPage() {
  const { user, accessToken, configured } = useAuth();
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

  const loadFromDb = useCallback(async () => {
    if (!accessToken) {
      setError("Connectez-vous pour charger vos données Supabase.");
      return;
    }
    setLoading(true);
    setError(null);
    setMode("db");
    try {
      const data = await fetchDashboard(accessToken);
      setKpis(data.kpis);
      setAlerts(data.alerts);
      setMatchStats(null);
      setMeta({ orders: data.orders_count, matches: data.matches_count });
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur seed");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (apiOk && !user) {
      void loadLocalDemo();
    }
    if (apiOk && user && accessToken) {
      void loadFromDb();
    }
  }, [apiOk, user, accessToken, loadLocalDemo, loadFromDb]);

  const profitTone =
    kpis == null ? "default" : kpis.net_profit >= 0 ? "positive" : "negative";

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
                onClick={() => void loadFromDb()}
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

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard label="Dépense pub" value={formatMad(kpis?.total_ad_spend)} hint="Meta + TikTok" />
        <KpiCard
          label="CA livré"
          value={formatMad(kpis?.delivered_revenue)}
          hint="Montants collectés"
          tone="accent"
        />
        <KpiCard
          label="Bénéfice net"
          value={formatMad(kpis?.net_profit)}
          hint="Après pub + frais retours"
          tone={profitTone}
        />
        <KpiCard
          label="ROAS réel"
          value={formatRoas(kpis?.real_roas)}
          hint="Revenu livré / dépense"
        />
        <KpiCard
          label="Taux de retour"
          value={formatPct(kpis?.global_return_rate)}
          hint={`${kpis?.total_returned ?? 0} retours / refus`}
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

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Campagnes
        </h2>
        <CampaignTable campaigns={kpis?.campaigns ?? []} />
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Alertes
        </h2>
        <AlertsList alerts={alerts} />
      </section>
    </AppShell>
  );
}
