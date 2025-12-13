import { NextRequest, NextResponse } from "next/server";

import {
  API_BASE,
  ACCESS_COOKIE_NAME,
  REFRESH_COOKIE_NAME,
  CSRF_COOKIE_NAME,
  buildBackendHeaders,
  clearAuthCookies,
  readJsonSafe,
} from "../utils";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get(REFRESH_COOKIE_NAME)?.value;
  const backendRes = await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    headers: buildBackendHeaders(req),
    body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : undefined,
  });

  const data = (await readJsonSafe(backendRes)) ?? {};
  const response = NextResponse.json(data, { status: backendRes.status });

  clearAuthCookies(response);
  response.cookies.delete(ACCESS_COOKIE_NAME);
  response.cookies.delete(CSRF_COOKIE_NAME);

  return response;
}
