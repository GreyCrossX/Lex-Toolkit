const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

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
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
    cache: "no-store",
  });
  const data = await handleJsonResponse(res);
  return data?.access_token as string;
}

export async function apiRefresh() {
  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
  });
  const data = await handleJsonResponse(res);
  return data?.access_token as string;
}

export async function apiLogout() {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = res.statusText || "Logout failed";
    throw new Error(detail);
  }
}
