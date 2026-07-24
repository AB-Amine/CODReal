const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type CampaignMetrics = {
  campaign_id: string;
  name: string;
  platform: string;
  total_spend: number;
  delivered_orders: number;
  returned_orders: number;
  refused_orders: number;
  pending_orders: number;
  total_matched_orders: number;
  net_revenue: number;
  return_fees: number;
  net_profit: number;
  real_cpa: number | null;
  real_roas: number | null;
  return_rate: number | null;
  performance_score: "excellent" | "good" | "warning" | "critical" | string;
  performance_label: string;
};

export type DashboardKPIs = {
  total_ad_spend: number;
  delivered_revenue: number;
  net_profit: number;
  real_roas: number | null;
  global_return_rate: number | null;
  total_delivered: number;
  total_returned: number;
  total_campaigns: number;
  campaigns: CampaignMetrics[];
};

export type AlertItem = {
  campaign_id: string;
  name: string;
  severity: "info" | "warning" | "critical";
  code: string;
  message: string;
};

export type PipelineResponse = {
  matching: {
    matches: Array<{
      campaign_id: string;
      order_id: string;
      match_type: string;
      confidence_score: number;
      normalized_phone: string | null;
    }>;
    stats: {
      total_orders: number;
      matched: number;
      unmatched_orders: number;
      match_rate: number;
      by_type?: Record<string, number>;
    };
    unmatched_orders: string[];
  };
  kpis: DashboardKPIs;
  alerts: AlertItem[];
};

export type UploadParseResult = {
  filename: string;
  valid_rows: Array<Record<string, unknown>>;
  errors: Array<{ row: number; field: string; message: string; value?: unknown }>;
  warnings: string[];
  columns_detected: string[];
  total_rows: number;
  valid_count: number;
  error_count: number;
  persisted?: boolean;
  persistence?: {
    orders_saved?: number;
    matches_saved?: number;
    matching?: PipelineResponse["matching"];
    kpis?: DashboardKPIs;
    alerts?: AlertItem[];
  };
};

function authHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : body.detail
            ? JSON.stringify(body.detail)
            : JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/** Wrap fetch so "Failed to fetch" becomes an actionable message. */
async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new Error(
      `Impossible de joindre l'API (${API_BASE}). ` +
        `1) Ouvre un terminal: cd D:\\CODREAL\\backend puis ` +
        `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload  ` +
        `2) Vérifie http://127.0.0.1:8000/api/v1/health  ` +
        `3) Frontend: http://localhost:3000 (pas un autre port)`
    );
  }
}

export async function healthCheck(): Promise<{ status: string; app: string; version: string }> {
  const res = await apiFetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
  return handle(res);
}

export async function authStatus(): Promise<{ supabase_configured: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/status`, { cache: "no-store" });
  return handle(res);
}

export async function fetchMe(token: string): Promise<{
  id: string;
  email: string | null;
  profile: Record<string, unknown>;
}> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export async function uploadDeliveryFile(
  file: File,
  options?: { token?: string | null; persist?: boolean }
): Promise<UploadParseResult> {
  const form = new FormData();
  form.append("file", file);
  const persist = options?.persist ? "true" : "false";
  const res = await apiFetch(`${API_BASE}/api/v1/orders/upload?persist=${persist}`, {
    method: "POST",
    headers: authHeaders(options?.token),
    body: form,
  });
  return handle(res);
}

export async function runPipeline(payload: unknown): Promise<PipelineResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/dashboard/pipeline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}

/** Instant local demo — no login, no sample JSON body. */
export async function runBuiltInDemo(): Promise<PipelineResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/demo/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return handle(res);
}

export async function fetchDashboard(
  token: string,
  days?: number,
  platform?: string
): Promise<{
  kpis: DashboardKPIs;
  alerts: AlertItem[];
  campaigns_count: number;
  orders_count: number;
  matches_count: number;
}> {
  const params = new URLSearchParams();
  if (days !== undefined) params.set("days", String(days));
  if (platform !== undefined) params.set("platform", platform);
  const q = params.toString() ? `?${params}` : "";
  const res = await apiFetch(`${API_BASE}/api/v1/dashboard/me${q}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export async function seedDemo(token: string): Promise<PipelineResponse & {
  orders_saved?: number;
  matches_saved?: number;
  kpis: DashboardKPIs;
  alerts: AlertItem[];
}> {
  const res = await apiFetch(`${API_BASE}/api/v1/dashboard/seed-demo`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return handle(res);
}

export async function listCampaigns(token: string): Promise<{
  campaigns: Array<Record<string, unknown>>;
  count: number;
}> {
  const res = await apiFetch(`${API_BASE}/api/v1/campaigns`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export type MetaStatus = {
  platform: string;
  configured: boolean;
  graph_version: string;
  scopes: string;
  redirect_uri: string;
  supabase_configured: boolean;
  mock_available: boolean;
  read_only: boolean;
};

export type MetaAdAccount = {
  id: string;
  platform: string;
  account_id: string;
  account_name: string | null;
  last_sync: string | null;
  token_expires_at: string | null;
  created_at: string;
};

export async function fetchMetaStatus(): Promise<MetaStatus> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/meta/status`, {
    cache: "no-store",
  });
  return handle(res);
}

export async function fetchMetaAccounts(token: string): Promise<{
  accounts: MetaAdAccount[];
  count: number;
}> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/meta/accounts`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export async function getMetaConnectUrl(token: string): Promise<{
  authorize_url: string;
  scopes: string;
  redirect_uri: string;
}> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/meta/connect`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export async function syncMeta(
  token: string,
  options?: { ad_account_id?: string; date_preset?: string }
): Promise<{
  ad_account: Record<string, unknown>;
  campaigns_synced: number;
  campaigns: Array<Record<string, unknown>>;
  date_preset: string;
}> {
  const params = new URLSearchParams();
  if (options?.ad_account_id) params.set("ad_account_id", options.ad_account_id);
  if (options?.date_preset) params.set("date_preset", options.date_preset);
  const q = params.toString() ? `?${params}` : "";
  const res = await fetch(`${API_BASE}/api/v1/integrations/meta/sync${q}`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return handle(res);
}

export async function mockConnectMeta(token: string): Promise<{
  account: MetaAdAccount;
  sync: { campaigns_synced: number };
  mode: string;
}> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/meta/mock-connect`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return handle(res);
}

export async function disconnectMeta(token: string, accountRowId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/integrations/meta/accounts/${accountRowId}`,
    {
      method: "DELETE",
      headers: authHeaders(token),
    }
  );
  await handle(res);
}

export type TikTokStatus = {
  platform: string;
  configured: boolean;
  redirect_uri: string;
  supabase_configured: boolean;
  mock_available: boolean;
  read_only: boolean;
};

export async function fetchTikTokStatus(): Promise<TikTokStatus> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/tiktok/status`, {
    cache: "no-store",
  });
  return handle(res);
}

export async function fetchTikTokAccounts(token: string): Promise<{
  accounts: MetaAdAccount[];
  count: number;
}> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/tiktok/accounts`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export async function getTikTokConnectUrl(token: string): Promise<{
  authorize_url: string;
  redirect_uri: string;
}> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/tiktok/connect`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export async function syncTikTok(
  token: string,
  options?: { ad_account_id?: string }
): Promise<{ campaigns_synced: number }> {
  const params = new URLSearchParams();
  if (options?.ad_account_id) params.set("ad_account_id", options.ad_account_id);
  const q = params.toString() ? `?${params}` : "";
  const res = await fetch(`${API_BASE}/api/v1/integrations/tiktok/sync${q}`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return handle(res);
}

export async function mockConnectTikTok(token: string): Promise<{
  sync: { campaigns_synced: number };
  mode: string;
}> {
  const res = await fetch(`${API_BASE}/api/v1/integrations/tiktok/mock-connect`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return handle(res);
}

export async function disconnectTikTok(token: string, accountRowId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/integrations/tiktok/accounts/${accountRowId}`,
    {
      method: "DELETE",
      headers: authHeaders(token),
    }
  );
  await handle(res);
}

export type UserSettings = {
  user_id?: string;
  return_fee_mad: number;
  critical_return_rate: number;
  target_roas: number;
};

export async function fetchUserSettings(token: string): Promise<UserSettings> {
  const res = await apiFetch(`${API_BASE}/api/v1/users/settings`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  return handle(res);
}

export async function saveUserSettings(
  token: string,
  settings: UserSettings
): Promise<UserSettings> {
  const res = await apiFetch(`${API_BASE}/api/v1/users/settings`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });
  return handle(res);
}

export { API_BASE };
