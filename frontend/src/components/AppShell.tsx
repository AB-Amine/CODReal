"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/upload", label: "Import CSV" },
  { href: "/campaigns", label: "Campagnes" },
  { href: "/integrations", label: "Intégrations" },
];

export function AppShell({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  const { user, configured, signOut, loading } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
              CR
            </span>
            <div>
              <p className="text-sm font-semibold leading-none">CODReal</p>
              <p className="text-[10px] text-slate-500">Real ROAS · COD Maroc</p>
            </div>
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-sm">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg px-3 py-1.5 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
              >
                {item.label}
              </Link>
            ))}
            {!loading && (
              <>
                {user ? (
                  <div className="ml-2 flex items-center gap-2 border-l border-slate-200 pl-3">
                    <span className="max-w-[140px] truncate text-xs text-slate-500">
                      {user.email}
                    </span>
                    <button
                      type="button"
                      onClick={() => void signOut()}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      Déconnexion
                    </button>
                  </div>
                ) : (
                  <Link
                    href="/login"
                    className="ml-2 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
                  >
                    {configured ? "Connexion" : "Connexion"}
                  </Link>
                )}
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        {title ? (
          <h1 className="mb-6 text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        ) : null}
        {children}
      </main>
    </div>
  );
}
