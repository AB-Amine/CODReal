"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { fetchUserSettings, saveUserSettings, type UserSettings } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const { user, accessToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [settings, setSettings] = useState<UserSettings>({
    return_fee_mad: 25.0,
    critical_return_rate: 0.30,
    target_roas: 2.0,
  });

  useEffect(() => {
    if (!accessToken) return;
    setFetching(true);
    fetchUserSettings(accessToken)
      .then((data) => {
        setSettings({
          return_fee_mad: data.return_fee_mad,
          critical_return_rate: data.critical_return_rate,
          target_roas: data.target_roas,
        });
      })
      .catch((err) => {
        console.error("Failed to load settings:", err);
      })
      .finally(() => {
        setFetching(false);
      });
  }, [accessToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken) {
      setError("Vous devez être connecté pour modifier vos réglages.");
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await saveUserSettings(accessToken, settings);
      setSuccess(true);
      // Hide success notification after 3s
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la sauvegarde.");
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <AppShell title="Réglages">
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          Veuillez vous connecter pour accéder aux réglages personnalisés.
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="Réglages">
      <div className="max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-slate-900">Seuils et Frais Personnalisés</h2>
          <p className="text-sm text-slate-500">
            Ajustez les seuils financiers utilisés pour calculer les performances et les alertes de vos campagnes.
          </p>
        </div>

        {fetching ? (
          <div className="py-8 text-center text-sm text-slate-500 animate-pulse">
            Chargement de vos réglages...
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="return-fee" className="block text-sm font-medium text-slate-700 mb-1.5">
                Frais de retour par défaut (MAD)
              </label>
              <input
                id="return-fee"
                type="number"
                step="0.01"
                min="0"
                required
                value={settings.return_fee_mad}
                onChange={(e) =>
                  setSettings({ ...settings, return_fee_mad: parseFloat(e.target.value) || 0 })
                }
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-indigo-500 focus:bg-white"
              />
              <p className="mt-1 text-xs text-slate-400">
                Coût logistique estimé par colis refusé ou retourné (ex: frais de transport retour).
              </p>
            </div>

            <div>
              <label htmlFor="return-rate" className="block text-sm font-medium text-slate-700 mb-1.5">
                Taux de retour critique (%)
              </label>
              <input
                id="return-rate"
                type="number"
                step="0.1"
                min="0"
                max="100"
                required
                value={settings.critical_return_rate * 100}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    critical_return_rate: (parseFloat(e.target.value) || 0) / 100,
                  })
                }
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-indigo-500 focus:bg-white"
              />
              <p className="mt-1 text-xs text-slate-400">
                Le taux de retour au-dessus duquel une alerte orange de vigilance est déclenchée (ex: 30%).
              </p>
            </div>

            <div>
              <label htmlFor="min-roas" className="block text-sm font-medium text-slate-700 mb-1.5">
                Objectif ROAS minimum
              </label>
              <input
                id="min-roas"
                type="number"
                step="0.1"
                min="0"
                required
                value={settings.target_roas}
                onChange={(e) =>
                  setSettings({ ...settings, target_roas: parseFloat(e.target.value) || 0 })
                }
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-indigo-500 focus:bg-white"
              />
              <p className="mt-1 text-xs text-slate-400">
                Le ROAS minimum requis pour qu&apos;une campagne soit marquée comme rentable (ex: 2.0x).
              </p>
            </div>

            {error && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-800">
                {error}
              </div>
            )}

            {success && (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-800">
                Réglages sauvegardés avec succès !
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="submit"
                disabled={loading}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
              >
                {loading ? "Enregistrement..." : "Enregistrer"}
              </button>
            </div>
          </form>
        )}
      </div>
    </AppShell>
  );
}
