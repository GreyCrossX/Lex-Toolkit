import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="relative mx-auto flex max-w-6xl items-center justify-between px-6 py-8">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-accent/40 bg-accent/15 text-xl font-semibold text-foreground shadow-lg shadow-accent/10">
            LT
          </div>
          <div>
            <p className="text-lg font-semibold">LexToolkit</p>
            <p className="text-sm text-muted">Inteligencia legal para despachos</p>
          </div>
        </div>
        <nav className="hidden items-center gap-4 text-sm text-muted md:flex">
          <Link href="/#platform" className="hover:text-accent">
            Plataforma
          </Link>
          <Link href="/#solutions" className="hover:text-accent">
            Soluciones
          </Link>
          <Link href="/pricing" className="hover:text-accent">
            Precios
          </Link>
          <Link href="/#impact" className="hover:text-accent">
            Impacto
          </Link>
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <Link
          href="/login"
          className="rounded-full border border-border px-4 py-2 text-sm text-foreground transition hover:border-accent hover:text-accent"
        >
          Iniciar sesión
        </Link>
        <Link
          href="/dashboard"
          className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-contrast transition hover:bg-accent-strong"
        >
          Ir al panel
        </Link>
      </div>
    </header>
  );
}
