"use client";

import Link from "next/link";
import { useState } from "react";
import { uploadDeliveryFile, type UploadParseResult } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Props = {
  onParsed?: (result: UploadParseResult) => void;
};

export function CsvUpload({ onParsed }: Props) {
  const { user, loading: authLoading, getAccessToken, configured } = useAuth();
  const [loading, setLoading] = useState(false);
  const [persist, setPersist] = useState(true);
  const [result, setResult] = useState<UploadParseResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getAccessToken();
      const wantPersist = persist && Boolean(token);

      if (persist && !token) {
        setError(
          "Vous devez être connecté pour enregistrer en base. Allez sur /login, puis réessayez."
        );
        setLoading(false);
        e.target.value = "";
        return;
      }

      const parsed = await uploadDeliveryFile(file, {
        token,
        persist: wantPersist,
      });
      setResult(parsed);
      onParsed?.(parsed);

      if (persist && !parsed.persisted) {
        setError(
          "Fichier validé mais non enregistré (pas de session). Connectez-vous et réessayez."
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur upload";
      if (msg.toLowerCase().includes("bearer") || msg.includes("401") || msg.includes("Authentification")) {
        setError(
          `${msg} — Déconnectez/reconnectez-vous sur /login, puis réessayez.`
        );
      } else {
        setError(msg);
      }
      setResult(null);
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Import livraisons (CSV / Excel)</h3>
      <p className="mt-1 text-xs text-slate-500">
        Colonnes: phone, status, amount_collected, delivery_date (+ order_ref, carrier, campaign_name)
      </p>

      {!configured ? (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Supabase frontend non configuré (NEXT_PUBLIC_SUPABASE_*). Persist impossible.
        </p>
      ) : null}

      {authLoading ? (
        <p className="mt-3 text-xs text-slate-500">Vérification de session…</p>
      ) : user ? (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-emerald-700">
            Connecté: <strong>{user.email}</strong> — token prêt pour l&apos;API
          </p>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={persist}
              onChange={(e) => setPersist(e.target.checked)}
              className="rounded border-slate-300"
            />
            Enregistrer en base + matching automatique
          </label>
        </div>
      ) : (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          Non connecté → validation seule (pas de sauvegarde).{" "}
          <Link href="/login" className="font-semibold text-indigo-700 underline">
            Se connecter
          </Link>{" "}
          ou{" "}
          <Link href="/signup" className="font-semibold text-indigo-700 underline">
            créer un compte
          </Link>
          . Pour une démo sans compte: Dashboard → <strong>Démo locale</strong>.
        </p>
      )}

      <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-8 transition hover:border-indigo-400 hover:bg-indigo-50/40">
        <span className="text-sm font-medium text-slate-700">
          {loading ? "Analyse en cours…" : "Choisir un fichier"}
        </span>
        <span className="mt-1 text-xs text-slate-400">.csv, .xlsx — max 5 Mo</span>
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={onFileChange}
          disabled={loading}
        />
      </label>

      {error ? (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      ) : null}

      {result ? (
        <div className="mt-4 space-y-2 text-sm">
          <p className="font-medium text-slate-800">
            {result.filename}: {result.valid_count}/{result.total_rows} lignes valides
            {result.persisted ? (
              <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">
                persisté · {result.persistence?.orders_saved ?? 0} cmd ·{" "}
                {result.persistence?.matches_saved ?? 0} matchs
              </span>
            ) : (
              <span className="ml-2 text-xs text-slate-400">(non enregistré)</span>
            )}
          </p>
          {result.warnings.map((w) => (
            <p key={w} className="text-amber-700">
              {w}
            </p>
          ))}
          {result.errors.slice(0, 5).map((e, i) => (
            <p key={i} className="text-xs text-rose-600">
              Ligne {e.row} · {e.field}: {e.message}
            </p>
          ))}
          {result.errors.length > 5 ? (
            <p className="text-xs text-slate-500">…et {result.errors.length - 5} autres erreurs</p>
          ) : null}
          {result.persistence?.kpis ? (
            <p className="text-xs text-slate-600">
              ROAS réel après import: {result.persistence.kpis.real_roas ?? "—"}x · Bénéfice:{" "}
              {result.persistence.kpis.net_profit} MAD
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
