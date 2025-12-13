import { clearAccessToken, getCsrfToken, setAccessToken } from "./auth";

const AUTH_BASE = "/api/auth";

async function handleJsonResponse(res: Response) {
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || res.statusText;
    throw new Error(`Auth request failed: ${detail}`);
  }
  return data;
}

export async function apiLogin(email: string, password: string) {
  const payload = { email: email.trim(), password: password.trim() };
  const res = await fetch(`${AUTH_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "include",
    cache: "no-store",
  });
  const data = await handleJsonResponse(res);
  if (data?.access_token) setAccessToken(data.access_token as string);
  return data?.access_token as string;
}

export async function apiRegister({
  email,
  password,
  fullName,
  role,
  firmId,
}: {
  email: string;
  password: string;
  fullName: string;
  role?: string;
  firmId?: string;
}) {
  const res = await fetch(`${AUTH_BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: email.trim(),
      password: password.trim(),
      full_name: fullName,
      role,
      firm_id: firmId,
    }),
    credentials: "include",
    cache: "no-store",
  });
  const data = await handleJsonResponse(res);
  if (data?.access_token) setAccessToken(data.access_token as string);
  return data?.access_token as string;
}

export async function apiRefresh() {
  const res = await fetch(`${AUTH_BASE}/refresh`, {
    method: "POST",
    headers: {
      ...(getCsrfToken() ? { "X-CSRF-Token": getCsrfToken() as string } : {}),
    },
    credentials: "include",
    cache: "no-store",
  });
  const data = await handleJsonResponse(res);
  if (data?.access_token) setAccessToken(data.access_token as string);
  return data?.access_token as string;
}

export async function apiLogout() {
  const res = await fetch(`${AUTH_BASE}/logout`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = res.statusText || "Logout failed";
    throw new Error(detail);
  }
  clearAccessToken();
}

export type AuthUser = {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  firm_id?: string | null;
};

export async function apiMe(): Promise<AuthUser> {
  const res = await fetch(`${AUTH_BASE}/me`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  const data = await handleJsonResponse(res);
  return data as AuthUser;
}
