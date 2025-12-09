import { NextRequest, NextResponse } from "next/server";

import {
  API_BASE,
  ACCESS_COOKIE_NAME,
  REFRESH_COOKIE_NAME,
  buildBackendHeaders,
  clearAuthCookies,
  readJsonSafe,
  setAccessCookie,
  setRefreshCookieFromBackend,
} from "../utils";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get(REFRESH_COOKIE_NAME)?.value;
  if (!refreshToken) {
    const unauth = NextResponse.json({ detail: "Refresh token missing" }, { status: 401 });
    clearAuthCookies(unauth);
    return unauth;
  }

  const backendRes = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: buildBackendHeaders(req),
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  const data = (await readJsonSafe(backendRes)) ?? {};
  const response = NextResponse.json(data, { status: backendRes.status });

  if (backendRes.ok && data?.access_token) {
    setAccessCookie(response, data.access_token);
  } else {
    response.cookies.delete(ACCESS_COOKIE_NAME);
  }
  setRefreshCookieFromBackend(backendRes, response);

  if (!backendRes.ok) {
    // If refresh failed, clear both cookies to force re-auth.
    clearAuthCookies(response);
  }

  return response;
}
