import { NextRequest, NextResponse } from "next/server";

const API_BASE =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://localhost:8000";

const isProd = process.env.NODE_ENV === "production";

export const ACCESS_COOKIE_NAME = "access_token";
export const REFRESH_COOKIE_NAME = "refresh_token";
export const CSRF_COOKIE_NAME = "csrf_token";
const REFRESH_MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // 7 days; mirrors backend default

type ParsedCookie = { token: string | null; maxAge?: number };

function parseCookie(setCookieHeader: string[] | undefined, name: string): ParsedCookie {
  if (!setCookieHeader) {
    return { token: null };
  }

  for (const raw of setCookieHeader) {
    const match = raw.match(new RegExp(`${name}=([^;]+)`));
    if (!match) continue;
    const maxAgeMatch = raw.match(/Max-Age=([^;]+)/i);
    const maxAge = maxAgeMatch ? Number.parseInt(maxAgeMatch[1], 10) : undefined;
    return { token: match[1], maxAge };
  }

  return { token: null };
}

export function setAccessCookie(response: NextResponse, token: string) {
  response.cookies.set({
    name: ACCESS_COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: 15 * 60, // 15 minutes; aligns with JWT default
  });
}

export function setRefreshCookieFromBackend(backendRes: Response, response: NextResponse) {
  // Node fetch exposes getSetCookie in Next; fall back to raw headers if needed.
  const setCookieHeader =
    (backendRes.headers as unknown as { getSetCookie?: () => string[] }).getSetCookie?.() ||
    // @ts-expect-error - raw() exists in node fetch
    backendRes.headers.raw?.()["set-cookie"] ||
    undefined;

  const { token, maxAge } = parseCookie(setCookieHeader, REFRESH_COOKIE_NAME);
  if (!token) return;

  response.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/api/auth/refresh",
    maxAge: maxAge ?? REFRESH_MAX_AGE_SECONDS,
  });
}

export function setCsrfCookieFromBackend(backendRes: Response, response: NextResponse) {
  const setCookieHeader =
    (backendRes.headers as unknown as { getSetCookie?: () => string[] }).getSetCookie?.() ||
    // @ts-expect-error - raw() exists in node fetch
    backendRes.headers.raw?.()["set-cookie"] ||
    undefined;

  const { token, maxAge } = parseCookie(setCookieHeader, CSRF_COOKIE_NAME);
  if (!token) return;

  response.cookies.set({
    name: CSRF_COOKIE_NAME,
    value: token,
    httpOnly: false,
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: maxAge ?? REFRESH_MAX_AGE_SECONDS,
  });
}

export function clearAuthCookies(response: NextResponse) {
  response.cookies.set({
    name: ACCESS_COOKIE_NAME,
    value: "",
    path: "/",
    maxAge: 0,
  });
  response.cookies.set({
    name: REFRESH_COOKIE_NAME,
    value: "",
    path: "/api/auth/refresh",
    maxAge: 0,
  });
  response.cookies.set({
    name: CSRF_COOKIE_NAME,
    value: "",
    path: "/",
    maxAge: 0,
  });
}

export async function readJsonSafe(res: Response) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export function buildBackendHeaders(req: NextRequest, contentTypeJson = true) {
  const headers = new Headers();
  if (contentTypeJson) {
    headers.set("content-type", "application/json");
  }
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) headers.set("x-forwarded-for", forwarded);
  return headers;
}

export { API_BASE };
