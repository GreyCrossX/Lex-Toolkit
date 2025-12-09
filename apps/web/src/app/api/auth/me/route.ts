import { NextRequest, NextResponse } from "next/server";

import { API_BASE, ACCESS_COOKIE_NAME, buildBackendHeaders, readJsonSafe } from "../utils";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const accessToken = req.cookies.get(ACCESS_COOKIE_NAME)?.value;
  if (!accessToken) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const headers = buildBackendHeaders(req, false);
  headers.set("authorization", `Bearer ${accessToken}`);

  const backendRes = await fetch(`${API_BASE}/auth/me`, {
    method: "GET",
    headers,
  });

  const data = (await readJsonSafe(backendRes)) ?? {};
  return NextResponse.json(data, { status: backendRes.status });
}
