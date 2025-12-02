/// <reference types="vitest" />
import { renderHook, waitFor } from "@testing-library/react";
import { useBackendHealth } from "./use-backend-health";
import { API_BASE_URL } from "@/lib/config";

const toast = vi.hoisted(() => ({
  error: vi.fn(),
  success: vi.fn(),
  info: vi.fn(),
}));

vi.mock("sonner", () => ({ toast }));

describe("useBackendHealth", () => {
  beforeEach(() => {
    toast.error.mockReset();
    vi.restoreAllMocks();
  });

  test("marks backend online when healthcheck succeeds", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }) as Response);

    const { result } = renderHook(() => useBackendHealth());

    await waitFor(() => expect(result.current).toBe("online"));
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/health`, { method: "GET" });
    expect(toast.error).not.toHaveBeenCalled();
  });

  test("marks backend offline and surfaces toast on failure", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useBackendHealth());

    await waitFor(() => expect(result.current).toBe("offline"));
    expect(toast.error).toHaveBeenCalled();
  });
});
