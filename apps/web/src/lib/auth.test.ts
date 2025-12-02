/// <reference types="vitest" />
import { clearFakeToken, getFakeToken, setFakeToken } from "./auth";

describe("auth localStorage helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("stores and retrieves fake token", () => {
    setFakeToken("demo-token");
    expect(getFakeToken()).toBe("demo-token");
  });

  test("clears fake token", () => {
    setFakeToken("demo-token");
    clearFakeToken();
    expect(getFakeToken()).toBeNull();
  });
});
