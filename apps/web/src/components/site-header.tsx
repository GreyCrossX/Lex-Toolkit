"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function SiteHeader() {
  const [hidden, setHidden] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    let lastY = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      const goingDown = y > lastY + 5;
      const goingUp = y < lastY - 5;
      setScrolled(y > 8);
      if (y < 16) {
        setHidden(false);
      } else if (goingDown) {
        setHidden(true);
      } else if (goingUp) {
        setHidden(false);
      }
      lastY = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const baseClasses =
    "fixed top-0 left-0 right-0 z-50 transition-all duration-300 backdrop-blur border-b border-border/40";
  const motionClasses = hidden ? "-translate-y-full opacity-70" : "translate-y-0 opacity-100";
  const paddingClasses = scrolled ? "py-3 bg-background/80 shadow-md shadow-black/10" : "py-6 bg-background/90";

  return (
    <header className={`${baseClasses} ${motionClasses} ${paddingClasses}`}>
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6">
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
        <div className="hidden items-center gap-3 md:flex">
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
        <button
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border text-sm text-foreground transition hover:border-accent hover:text-accent md:hidden"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Toggle navigation"
        >
          {menuOpen ? "✕" : "☰"}
        </button>
      </div>
      {menuOpen && (
        <div className="mx-4 mt-3 flex flex-col gap-3 rounded-2xl border border-border/60 bg-surface/90 p-4 text-sm text-muted md:hidden">
          <Link href="/#platform" className="hover:text-accent" onClick={() => setMenuOpen(false)}>
            Plataforma
          </Link>
          <Link href="/#solutions" className="hover:text-accent" onClick={() => setMenuOpen(false)}>
            Soluciones
          </Link>
          <Link href="/pricing" className="hover:text-accent" onClick={() => setMenuOpen(false)}>
            Precios
          </Link>
          <Link href="/#impact" className="hover:text-accent" onClick={() => setMenuOpen(false)}>
            Impacto
          </Link>
          <div className="mt-2 flex flex-col gap-2">
            <Link
              href="/login"
              className="rounded-full border border-border px-4 py-2 text-foreground transition hover:border-accent hover:text-accent"
              onClick={() => setMenuOpen(false)}
            >
              Iniciar sesión
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full bg-accent px-4 py-2 text-center font-semibold text-contrast transition hover:bg-accent-strong"
              onClick={() => setMenuOpen(false)}
            >
              Ir al panel
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
