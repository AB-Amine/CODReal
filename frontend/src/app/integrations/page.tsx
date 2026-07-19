"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import {
  disconnectMeta,
  disconnectTikTok,
  fetchMetaAccounts,
  fetchMetaStatus,
  fetchTikTokAccounts,
  fetchTikTokStatus,
  getMetaConnectUrl,
  getTikTokConnectUrl,
  mockConnectMeta,
  mockConnectTikTok,
  syncMeta,
  syncTikTok,
  type MetaAdAccount,
  type MetaStatus,
  type TikTokStatus,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function IntegrationsContent() {
  const { user, accessToken, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [metaStatus, setMetaStatus] = useState<MetaStatus | null>(null);
  const [ttStatus, setTtStatus] = useState<TikTokStatus | null>(null);
  const [metaAccounts, setMetaAccounts] = useState<MetaAdAccount[]>([]);
  const [ttAccounts, setTtAccounts] = useState<MetaAdAccount[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [ms, ts] = await Promise.all([fetchMetaStatus(), fetchTikTokStatus()]);
      setMetaStatus(ms);
      setTtStatus(ts);
      if (accessToken) {
        const [ma, ta] = await Promise.all([
          fetchMetaAccounts(accessToken),
          fetchTikTokAccounts(accessToken),
        ]);
        setMetaAccounts(ma.accounts);
        setTtAccounts(ta.accounts);
      } else {
        setMetaAccounts([]);
        setTtAccounts([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur chargement");
    }
  }, [accessToken]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const meta = searchParams.get("meta");
    const tiktok = searchParams.get("tiktok");
    const message = searchParams.get("message");
    if (meta === "connected") {
      setInfo(`Compte Meta connecté (${searchParams.get("accounts") || "?"} ad account(s)).`);
    } else if (meta === "error") {
      setError(message || "Erreur OAuth Meta");
    }
    if (tiktok === "connected") {
      setInfo(`Compte TikTok connecté (${searchParams.get("accounts") || "?"} advertiser(s)).`);
    } else if (tiktok === "error") {
      setError(message || "Erreur OAuth TikTok");
    }
  }, [searchParams]);

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError(null);
    setInfo(null);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppShell title="Intégrations publicitaires">
      <p className="mb-6 max-w-2xl text-sm text-slate-600">
        Lecture seule Meta + TikTok. Tokens chiffrés côté serveur. Sans app réelle, utilisez les
        mocks (nécessite login + Supabase).
      </p>

      {!authLoading && !user ? (
        <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950">
          <p className="font-medium">Connexion requise pour connecter les comptes ads</p>
          <p className="mt-1 text-xs">
            Sans Supabase configuré, le login ne marchera pas encore — voir{" "}
            <code>docs/YOU_MUST_PROVIDE.md</code>
          </p>
          <Link
            href="/login"
            className="mt-3 inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
          >
            Se connecter
          </Link>
        </div>
      ) : null}

      {error ? (
        <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}
      {info ? (
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {info}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Meta */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#1877F2] text-sm font-bold text-white">
                f
              </span>
              <div>
                <h2 className="font-semibold">Meta Ads</h2>
                <p className="text-xs text-slate-500">Facebook / Instagram · lecture seule</p>
              </div>
            </div>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                metaStatus?.configured
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {metaStatus?.configured ? "App OK" : "Mock only"}
            </span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!user || !accessToken || !!busy || !metaStatus?.configured}
              onClick={() =>
                void run("meta-oauth", async () => {
                  const { authorize_url } = await getMetaConnectUrl(accessToken!);
                  window.location.href = authorize_url;
                })
              }
              className="rounded-lg bg-[#1877F2] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              Connecter OAuth
            </button>
            <button
              type="button"
              disabled={!user || !accessToken || !!busy}
              onClick={() =>
                void run("meta-mock", async () => {
                  const r = await mockConnectMeta(accessToken!);
                  setInfo(`Mock Meta — ${r.sync.campaigns_synced} campagnes.`);
                })
              }
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium disabled:opacity-50"
            >
              Mock démo
            </button>
            {metaAccounts.length > 0 ? (
              <button
                type="button"
                disabled={!!busy}
                onClick={() =>
                  void run("meta-sync", async () => {
                    const r = await syncMeta(accessToken!);
                    setInfo(`Sync Meta — ${r.campaigns_synced} campagnes.`);
                  })
                }
                className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                Sync
              </button>
            ) : null}
          </div>
          <AccountTable
            accounts={metaAccounts}
            busy={busy}
            onSync={(id) =>
              void run(`ms-${id}`, async () => {
                const r = await syncMeta(accessToken!, { ad_account_id: id });
                setInfo(`Sync Meta — ${r.campaigns_synced} campagnes.`);
              })
            }
            onDisconnect={(id) =>
              void run(`md-${id}`, async () => {
                await disconnectMeta(accessToken!, id);
                setInfo("Meta déconnecté.");
              })
            }
          />
        </div>

        {/* TikTok */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white">
                TT
              </span>
              <div>
                <h2 className="font-semibold">TikTok Ads</h2>
                <p className="text-xs text-slate-500">Marketing API · lecture seule</p>
              </div>
            </div>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                ttStatus?.configured
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {ttStatus?.configured ? "App OK" : "Mock only"}
            </span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!user || !accessToken || !!busy || !ttStatus?.configured}
              onClick={() =>
                void run("tt-oauth", async () => {
                  const { authorize_url } = await getTikTokConnectUrl(accessToken!);
                  window.location.href = authorize_url;
                })
              }
              className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              Connecter OAuth
            </button>
            <button
              type="button"
              disabled={!user || !accessToken || !!busy}
              onClick={() =>
                void run("tt-mock", async () => {
                  const r = await mockConnectTikTok(accessToken!);
                  setInfo(`Mock TikTok — ${r.sync.campaigns_synced} campagnes.`);
                })
              }
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium disabled:opacity-50"
            >
              Mock démo
            </button>
            {ttAccounts.length > 0 ? (
              <button
                type="button"
                disabled={!!busy}
                onClick={() =>
                  void run("tt-sync", async () => {
                    const r = await syncTikTok(accessToken!);
                    setInfo(`Sync TikTok — ${r.campaigns_synced} campagnes.`);
                  })
                }
                className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                Sync
              </button>
            ) : null}
          </div>
          <AccountTable
            accounts={ttAccounts}
            busy={busy}
            onSync={(id) =>
              void run(`ts-${id}`, async () => {
                const r = await syncTikTok(accessToken!, { ad_account_id: id });
                setInfo(`Sync TikTok — ${r.campaigns_synced} campagnes.`);
              })
            }
            onDisconnect={(id) =>
              void run(`td-${id}`, async () => {
                await disconnectTikTok(accessToken!, id);
                setInfo("TikTok déconnecté.");
              })
            }
          />
        </div>
      </div>

      <p className="mt-6 text-xs text-slate-500">
        Après sync →{" "}
        <Link href="/campaigns" className="text-indigo-600">
          Campagnes
        </Link>{" "}
        + import CSV livraisons pour le ROAS réel. Cron:{" "}
        <code>scripts/run_sync.ps1</code>
      </p>
    </AppShell>
  );
}

function AccountTable({
  accounts,
  busy,
  onSync,
  onDisconnect,
}: {
  accounts: MetaAdAccount[];
  busy: string | null;
  onSync: (id: string) => void;
  onDisconnect: (id: string) => void;
}) {
  if (!accounts.length) {
    return (
      <p className="mt-4 text-xs text-slate-400">Aucun compte connecté sur cette plateforme.</p>
    );
  }
  return (
    <ul className="mt-4 space-y-2">
      {accounts.map((a) => (
        <li
          key={a.id}
          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
        >
          <div>
            <p className="font-medium text-slate-900">
              {a.account_name || a.account_id}
              {a.account_id?.startsWith("mock-") ? (
                <span className="ml-2 rounded bg-amber-100 px-1 text-[10px] font-bold text-amber-800">
                  MOCK
                </span>
              ) : null}
            </p>
            <p className="font-mono text-[10px] text-slate-500">{a.account_id}</p>
          </div>
          <div className="flex gap-2 text-xs">
            <button
              type="button"
              disabled={!!busy}
              onClick={() => onSync(a.id)}
              className="font-medium text-indigo-600"
            >
              Sync
            </button>
            <button
              type="button"
              disabled={!!busy}
              onClick={() => onDisconnect(a.id)}
              className="font-medium text-rose-600"
            >
              Off
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function IntegrationsPage() {
  return (
    <Suspense
      fallback={
        <AppShell title="Intégrations">
          <p className="text-sm text-slate-500">Chargement…</p>
        </AppShell>
      }
    >
      <IntegrationsContent />
    </Suspense>
  );
}
