const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AuthTokens = {
  accessToken: string;
  refreshToken: string;
};

type ApiErrorShape = {
  detail?: string | Array<{ msg?: string }>;
};

function getApiBaseUrl() {
  return DEFAULT_API_URL.replace(/\/$/, "");
}

function getStoredAuth(): AuthTokens | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem("entropy-auth");
    return raw ? (JSON.parse(raw) as AuthTokens) : null;
  } catch {
    return null;
  }
}

export function saveAuth(tokens: AuthTokens) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("entropy-auth", JSON.stringify(tokens));
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("entropy-auth");
}

export function getAuthToken() {
  return getStoredAuth()?.accessToken ?? null;
}

export function getActiveOrgId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("entropy-org-id");
}

export function setActiveOrgId(orgId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("entropy-org-id", orgId);
}

async function request<T>(path: string, init: RequestInit = {}, requireAuth = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  if (requireAuth) {
    const token = getAuthToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorShape | null;
    const detail = Array.isArray(body?.detail)
      ? body?.detail[0]?.msg
      : body?.detail ?? "Request failed";
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; refresh_token: string; token_type: string }>(
    "/api/v1/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ email, password }),
    },
    false,
  );
}

export async function register(email: string, password: string, fullName?: string) {
  return request<{ id: string; email: string; full_name: string | null; is_active: boolean }>(
    "/api/v1/auth/register",
    {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName ?? null }),
    },
    false,
  );
}

export async function getMe() {
  return request<{ id: string; email: string; full_name: string | null; is_active: boolean }>(
    "/api/v1/users/me",
  );
}

export async function getOrganizations() {
  return request<Array<{ id: string; name: string; slug: string; created_at: string }>>(
    "/api/v1/organizations",
  );
}

export async function quickScan(target: string) {
  return request<{ scan_job_id: string; org_id: string; status: string }>(
    "/api/v1/quick-scan",
    {
      method: "POST",
      body: JSON.stringify({
        target,
        target_type: "domain",
        scan_type: "default",
        skip_verification: true,
      }),
    },
    false,
  );
}

export async function getScanJob(scanJobId: string, orgId: string) {
  return request<{
    id: string;
    domain_id: string;
    status: string;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    scan_type: string;
  }>(`/api/v1/scan-jobs/${scanJobId}`, {
    headers: {
      "X-Organization-ID": orgId,
    },
  });
}

export async function listScanJobs(orgId: string) {
  return request<Array<{
    id: string;
    domain_id: string;
    status: string;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    scan_type: string;
  }>>(`/api/v1/scan-jobs`, {
    headers: {
      "X-Organization-ID": orgId,
    },
  });
}

export async function getDomain(domainId: string, orgId: string) {
  return request<{ id: string; hostname: string; verification_status: string | null }>(
    `/api/v1/domains/${domainId}`,
    {
      headers: {
        "X-Organization-ID": orgId,
      },
    },
  );
}

export async function getScanResults(scanJobId: string, orgId: string) {
  return request<Array<{
    id: string;
    scan_job_id: string;
    summary: Record<string, unknown>;
    severity_counts: Record<string, number>;
    created_at: string;
  }>>(`/api/v1/scan-jobs/${scanJobId}/results`, {
    headers: {
      "X-Organization-ID": orgId,
    },
  });
}
