import Link from "next/link";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-slate-50">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-4 py-5">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white">
            CR
          </span>
          <span className="font-semibold text-slate-900">CODReal</span>
        </div>
        <Link
          href="/dashboard"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
        >
          Ouvrir le dashboard
        </Link>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-20 pt-10">
        <p className="text-sm font-medium text-indigo-600">Phase 1 · MVP</p>
        <h1 className="mt-3 max-w-2xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          Combien tu gagnes{" "}
          <span className="text-indigo-600">vraiment</span> avec tes pubs COD ?
        </h1>
        <p className="mt-5 max-w-xl text-lg text-slate-600">
          CODReal croise tes dépenses Meta/TikTok avec tes livraisons réelles. ROAS réel, CPA
          réel, bénéfice net — après retours et frais.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/dashboard"
            className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow hover:bg-indigo-500"
          >
            Voir la démo dashboard
          </Link>
          <Link
            href="/signup"
            className="rounded-xl border border-indigo-200 bg-indigo-50 px-5 py-3 text-sm font-semibold text-indigo-800 shadow-sm hover:bg-indigo-100"
          >
            Créer un compte
          </Link>
          <Link
            href="/upload"
            className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-50"
          >
            Importer un CSV
          </Link>
        </div>

        <div className="mt-16 grid gap-4 sm:grid-cols-3">
          {[
            {
              t: "Matching intelligent",
              d: "Téléphone normalisé (+212 / 0) + ID commande — le cœur du produit.",
            },
            {
              t: "KPIs réels COD",
              d: "Bénéfice net, ROAS réel, CPA sur livrés, taux de retour.",
            },
            {
              t: "Alertes claires",
              d: "Repère vite les campagnes perdantes avant de brûler le budget.",
            },
          ].map((card) => (
            <div
              key={card.t}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <h3 className="font-semibold text-slate-900">{card.t}</h3>
              <p className="mt-2 text-sm text-slate-600">{card.d}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
