/// <reference types="vitest" />
import { clearAccessToken, getAccessToken, setAccessToken } from "./auth";

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
});
