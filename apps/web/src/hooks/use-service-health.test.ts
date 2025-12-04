import { renderHook, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { useServiceHealth } from "./use-service-health";

describe("useServiceHealth", () => {
  test("marks service online on 200", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 });

    const { result } = renderHook(() => useServiceHealth("/summary/health", 10));

    await waitFor(() => expect(result.current.status).toBe("online"), { timeout: 200 });
    expect(result.current.error).toBeNull();
  });

  test("marks service offline on non-200", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 });

    const { result } = renderHook(() => useServiceHealth("/summary/health", 10));

    await waitFor(() => expect(result.current.status).toBe("offline"), { timeout: 200 });
    expect(result.current.error).toMatch(/HTTP 500/);
  });
});
