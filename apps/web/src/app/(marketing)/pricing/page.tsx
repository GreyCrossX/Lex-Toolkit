"use client";

import Link from "next/link";
import { Check, Shield, Headset, Lock, ArrowRight } from "lucide-react";
import { SiteHeader } from "@/components/site-header";

const plans = [
  {
    name: "Starter",
    price: "USD 49",
    cadence: "usuario/mes",
    badge: "Ideal para pilotos",
    description: "Para equipos pequeños que quieren probar búsqueda, Q&A y resúmenes con trazabilidad.",
    highlights: [
      "Búsqueda vectorial y Q&A con citas",
      "Resúmenes de 1 documento",
      "5 workspaces",
      "Hasta 20k documentos en Vault",
      "Soporte por email",
    ],
    cta: "Probar ahora",
  },
  {
    name: "Professional",
    price: "USD 129",
    cadence: "usuario/mes",
    badge: "Más popular",
    description: "Para despachos y equipos internos que necesitan flujos completos y control de seguridad.",
    highlights: [
      "Todo Starter",
      "Resúmenes multi-documento",
      "Workflows y plantillas de redacción",
      "SSO / JWT ready",
      "Límites ampliados de Vault (100k docs)",
      "Soporte prioritario",
    ],
    cta: "Hablar con ventas",
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    cadence: "acuerdo anual",
    badge: "A la medida",
    description: "Para firmas grandes y corporativos: despliegues dedicados y cumplimiento avanzado.",
    highlights: [
      "Todo Professional",
      "Despliegue dedicado / VPC",
      "Retención y auditoría personalizadas",
      "Integración con DLP / SIEM",
      "Soporte 24/7 y CSM",
      "SLAs y métricas de calidad",
    ],
    cta: "Solicitar demo",
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <div className="mx-auto max-w-5xl px-6 pb-12">
        <div className="mt-4 flex flex-col gap-4 text-center">
          <p className="inline-flex items-center gap-2 self-center rounded-full border border-accent/30 bg-accent/10 px-4 py-1 text-xs font-semibold text-accent">
            Planes flexibles
          </p>
          <h1 className="text-4xl font-semibold">Precios claros para cada etapa.</h1>
          <p className="text-lg text-muted">
            Elige entre piloto, despliegue profesional o enterprise dedicado. Ajusta consumo y autenticación según tu
            stack.
          </p>
          <div className="flex flex-wrap justify-center gap-3 text-sm text-muted">
            <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-2">
              <Shield className="h-4 w-4 text-accent" />
              Sin entrenar modelos con tus datos
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-2">
              <Lock className="h-4 w-4 text-accent" />
              Listo para JWT / SSO
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-2">
              <Headset className="h-4 w-4 text-accent" />
              Soporte incluido en todos los planes
            </span>
          </div>
        </div>

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-3xl border border-border/60 bg-surface/80 p-6 shadow-lg shadow-black/20 ${
                plan.featured ? "ring-2 ring-accent/50" : ""
              }`}
            >
              {plan.badge ? (
                <span className="inline-flex rounded-full border border-accent/40 bg-accent/15 px-3 py-1 text-[11px] font-semibold text-accent">
                  {plan.badge}
                </span>
              ) : null}
              <div className="mt-4 flex items-baseline gap-2">
                <p className="text-3xl font-semibold">{plan.price}</p>
                <p className="text-sm text-muted">/{plan.cadence}</p>
              </div>
              <p className="mt-1 text-xl font-semibold">{plan.name}</p>
              <p className="mt-2 text-sm text-muted">{plan.description}</p>

              <ul className="mt-4 space-y-2 text-sm text-muted">
                {plan.highlights.map((item) => (
                  <li key={item} className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-accent" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>

              <Link
                href={plan.featured ? "/login" : "/dashboard"}
                className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                  plan.featured
                    ? "bg-accent text-contrast hover:bg-accent-strong"
                    : "border border-border text-foreground hover:border-accent hover:text-accent"
                }`}
              >
                {plan.cta}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap justify-center gap-3 text-sm text-muted">
          <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-2">
            Ajusta consumo por usuario o por volumen de documentos
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-2">
            Plan Enterprise incluye despliegue dedicado y SLAs
          </span>
        </div>

        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Link
            href="/dashboard"
            className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong"
          >
            Probar ahora
          </Link>
          <Link
            href="/login"
            className="rounded-full border border-border px-6 py-3 text-sm font-semibold text-foreground transition hover:border-accent hover:text-accent"
          >
            Solicitar demo
          </Link>
        </div>
      </div>
    </div>
  );
}
