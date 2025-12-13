import { NextRequest, NextResponse } from "next/server";

import {
  API_BASE,
  ACCESS_COOKIE_NAME,
  buildBackendHeaders,
  readJsonSafe,
  setAccessCookie,
  setRefreshCookieFromBackend,
  setCsrfCookieFromBackend,
} from "../utils";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const backendRes = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: buildBackendHeaders(req),
    body: JSON.stringify(body),
  });

  const data = (await readJsonSafe(backendRes)) ?? {};
  const response = NextResponse.json(data, { status: backendRes.status });

  if (backendRes.ok && data?.access_token) {
    setAccessCookie(response, data.access_token);
  } else {
    response.cookies.delete(ACCESS_COOKIE_NAME);
  }
  setRefreshCookieFromBackend(backendRes, response);
  setCsrfCookieFromBackend(backendRes, response);

  return response;
}
