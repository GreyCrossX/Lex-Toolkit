/// <reference types="vitest" />
import { clearAccessToken, getAccessToken, getCsrfToken, setAccessToken } from "./auth";

describe("auth access token memory store", () => {
  beforeEach(() => {
    clearAccessToken();
  });

  test("stores and retrieves access token", () => {
    setAccessToken("demo-token");
    expect(getAccessToken()).toBe("demo-token");
  });

  test("clears access token", () => {
    setAccessToken("demo-token");
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });

  test("reads csrf_token from document.cookie when available", () => {
    Object.defineProperty(global, "document", {
      value: {
        cookie: "foo=bar; csrf_token=abc123; other=1",
      },
      writable: true,
    });
    expect(getCsrfToken()).toBe("abc123");
  });
});
