import { apiRefresh } from "./auth-client";
import { clearAccessToken, getAccessToken, setAccessToken } from "./auth";

type AuthFetchInit = RequestInit & { _retry?: boolean };

function withAuthHeaders(init: AuthFetchInit, token: string | null) {
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return {
    ...init,
    headers,
    credentials: "include" as const,
    cache: init.cache ?? "no-store",
  };
}

export async function authFetch(input: RequestInfo | URL, init: AuthFetchInit = {}) {
  const token = getAccessToken();
  const firstRes = await fetch(input, withAuthHeaders(init, token));
  if (firstRes.status !== 401 || init._retry === false) {
    return firstRes;
  }

  try {
    const newToken = await apiRefresh();
    if (newToken) {
      setAccessToken(newToken);
    }
    const retryInit: AuthFetchInit = { ...init, _retry: false };
    return await fetch(input, withAuthHeaders(retryInit, newToken ?? null));
  } catch (error) {
    clearAccessToken();
    throw error;
  }
}
