/// <reference types="vitest" />
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import DashboardPage, { formatList } from "./page";

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}));

vi.mock("sonner", () => ({ toast }));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));
vi.mock("@/hooks/use-backend-health", () => ({
  useBackendHealth: () => "online",
}));
vi.mock("@/hooks/use-customer-context", () => ({
  useCustomerContext: () => ({
    user: null,
    firmId: null,
    loading: false,
    error: null,
    isAuthenticated: false,
  }),
}));

describe("formatList", () => {
  test("splits comma separated values and trims", () => {
    expect(formatList(" a, b , ,c")).toEqual(["a", "b", "c"]);
    expect(formatList("")).toEqual([]);
  });
});

describe("DashboardPage search flows", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    toast.success.mockReset();
    toast.error.mockReset();
    toast.info.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function fillSearchForm() {
    fireEvent.change(screen.getByPlaceholderText("Ej. requisitos para licitaciones en CDMX"), {
      target: { value: "hola" },
    });
    fireEvent.change(screen.getByPlaceholderText("doc123, doc456"), {
      target: { value: "doc-1, doc-2" },
    });
    fireEvent.change(screen.getByPlaceholderText("cdmx, federal"), {
      target: { value: "CDMX" },
    });
    fireEvent.change(screen.getByPlaceholderText("artículo, capítulo"), {
      target: { value: "art" },
    });
  }

  test("runs QA mode against /qa with formatted body and sorts citations", async () => {
    fetchMock.mockImplementation((url, options) => {
      if (url.toString().includes("/qa")) {
        const body = JSON.parse((options as RequestInit).body as string);
        expect(body.top_k).toBe(3);
        expect(body.doc_ids).toEqual(["doc-1", "doc-2"]);
        expect(body.jurisdictions).toEqual(["CDMX"]);
        expect(body.sections).toEqual(["art"]);
        return Promise.resolve(
          new Response(
            JSON.stringify({
              answer: "respuesta",
              citations: [
                { chunk_id: "c1", doc_id: "doc-1", section: "s1", jurisdiction: "cdmx", content: "A", distance: 0.4 },
                { chunk_id: "c2", doc_id: "doc-2", section: "s2", jurisdiction: "cdmx", content: "B", distance: 0.2 },
              ],
            }),
            { status: 200 }
          )
        );
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    render(<DashboardPage />);
    fillSearchForm();
    fireEvent.change(screen.getByLabelText("Resultados (top_k)"), { target: { value: "3" } });

    fireEvent.click(screen.getByRole("button", { name: "Ejecutar búsqueda / Q&A" }));

    await screen.findByText("respuesta");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/qa"), expect.anything()));

    let citations = await screen.findAllByRole("listitem");
    expect(citations[0].textContent).toContain("doc-2");

    fireEvent.click(screen.getByRole("button", { name: /Ordenar por distancia/ }));

    await waitFor(() => {
      citations = screen.getAllByRole("listitem");
      expect(within(citations[0]).getByText(/doc-1/)).toBeInTheDocument();
    });
  });

  test("runs search mode against /search with limit instead of top_k", async () => {
    fetchMock.mockImplementation((url, options) => {
      if (url.toString().includes("/search")) {
        const body = JSON.parse((options as RequestInit).body as string);
        expect(body.limit).toBe(4);
        expect(body.top_k).toBeUndefined();
        return Promise.resolve(
          new Response(
            JSON.stringify({
              results: [{ chunk_id: "c3", doc_id: "doc-3", section: "s3", jurisdiction: "cdmx", content: "C", distance: 0.1 }],
            }),
            { status: 200 }
          )
        );
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Búsqueda (lista de resultados)" }));
    fillSearchForm();
    fireEvent.change(screen.getByLabelText("Resultados (top_k)"), { target: { value: "4" } });

    fireEvent.click(screen.getByRole("button", { name: "Ejecutar búsqueda / Q&A" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/search"), expect.anything()));
    await screen.findByText("doc-3");
  });

  test("surfaces toast error when backend responds non-200", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    fetchMock.mockImplementation((url) => {
      if (url.toString().includes("/qa")) {
        return Promise.resolve(new Response("boom", { status: 500 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    render(<DashboardPage />);
    fillSearchForm();

    fireEvent.click(screen.getByRole("button", { name: "Ejecutar búsqueda / Q&A" }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });
});

describe("DashboardPage summary and upload flows", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    toast.success.mockReset();
    toast.error.mockReset();
    toast.info.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  function selectTool(label: string) {
    fireEvent.click(screen.getByRole("button", { name: label }));
  }

  test("runs summary and renders citations", async () => {
    fetchMock.mockImplementation((url, options) => {
      const u = url.toString();
      const method = (options as RequestInit | undefined)?.method;
      if (u.includes("/summary") && method === "POST") {
        const ndjson = [
          JSON.stringify({
            type: "citation",
            data: { chunk_id: "c1", doc_id: "doc-1", section: "s1", jurisdiction: "mx", content: "texto" },
          }),
          JSON.stringify({ type: "summary_chunk", data: "Resumen " }),
          JSON.stringify({ type: "summary_chunk", data: "listo" }),
          JSON.stringify({ type: "done", data: { model: "stub", chunks_used: 1 } }),
        ].join("\n");
        return Promise.resolve(
          new Response(ndjson, {
            status: 200,
            headers: { "Content-Type": "application/x-ndjson" },
          })
        );
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    render(<DashboardPage />);
    selectTool("Resumen de un documento");

    fireEvent.change(screen.getByPlaceholderText("Pega texto a resumir..."), {
      target: { value: "texto para resumir" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generar resumen" }));

    await screen.findByText("Resumen listo");
    expect(screen.getByText(/doc-1/)).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalled();
  });

  test("summary shows placeholder and error toast on failure", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    fetchMock.mockImplementation((url, options) => {
      const u = url.toString();
      const method = (options as RequestInit | undefined)?.method;
      if (u.includes("/summary") && method === "POST") {
        return Promise.resolve(new Response("boom", { status: 500 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    render(<DashboardPage />);
    selectTool("Resumen de un documento");

    fireEvent.change(screen.getByPlaceholderText("Pega texto a resumir..."), {
      target: { value: "texto fallido" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generar resumen" }));

    await screen.findByText(/Resumen placeholder/);
    expect(toast.error).toHaveBeenCalled();
  });

  test("upload succeeds and updates status", async () => {
    fetchMock.mockImplementation((url, options) => {
      const method = (options as RequestInit | undefined)?.method;
      if (url.toString().includes("/upload") && method === "POST") {
        expect((options as RequestInit).body).toBeInstanceOf(FormData);
        return Promise.resolve(
          new Response(JSON.stringify({ job_id: "job-1", status: "queued", message: "en cola" }), { status: 200 })
        );
      }
      if (url.toString().includes("/upload/job-1")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              job_id: "job-1",
              filename: "demo.pdf",
              status: "completed",
              progress: 100,
              doc_ids: ["doc-1"],
            }),
            { status: 200 }
          )
        );
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const { container } = render(<DashboardPage />);
    selectTool("Carga de documentos");

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["hello"], "demo.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await screen.findByText(/Estado: completed/);
    expect(toast.success).toHaveBeenCalled();
  });

  test("upload surfaces placeholder and error toast on failure", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    fetchMock.mockImplementation((url, options) => {
      const method = (options as RequestInit | undefined)?.method;
      if (url.toString().includes("/upload") && method === "POST") {
        return Promise.resolve(new Response("fail", { status: 500 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const { container } = render(<DashboardPage />);
    selectTool("Carga de documentos");

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["hello"], "demo.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await screen.findByText(/No se pudo iniciar la ingesta/);
    expect(toast.error).toHaveBeenCalled();
  });
});
