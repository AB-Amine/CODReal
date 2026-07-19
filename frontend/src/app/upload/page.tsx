"use client";

import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { CsvUpload } from "@/components/CsvUpload";

export default function UploadPage() {
  return (
    <AppShell title="Import des livraisons">
      <div className="grid gap-6 lg:grid-cols-2">
        <CsvUpload />
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Template recommandé</h3>
          <p className="mt-2 text-sm text-slate-600">
            Utilisez le fichier d&apos;exemple du repo:{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">
              samples/codreal_delivery_template.csv
            </code>
          </p>
          <ul className="mt-4 list-inside list-disc space-y-1 text-sm text-slate-600">
            <li>
              <strong>phone</strong> — obligatoire (formats MA acceptés)
            </li>
            <li>
              <strong>status</strong> — delivered / returned / refused / pending (ou FR: livré,
              retour…)
            </li>
            <li>
              <strong>amount_collected</strong> — MAD
            </li>
            <li>
              <strong>delivery_date</strong> — date de livraison
            </li>
            <li>
              <strong>order_ref</strong> — optionnel, matching secondaire
            </li>
          </ul>
          <p className="mt-4 text-xs text-slate-500">
            Phase 1: validation + preview. Persistance Supabase dans la prochaine itération.
          </p>
          <Link
            href="/dashboard"
            className="mt-6 inline-flex text-sm font-medium text-indigo-600 hover:text-indigo-500"
          >
            ← Retour dashboard
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
