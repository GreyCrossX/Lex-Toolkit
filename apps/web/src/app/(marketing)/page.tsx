import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  Shield,
  Sparkles,
  BookOpenCheck,
  FileSearch,
  ScrollText,
  Bot,
  Clock3,
  ShieldCheck,
  Workflow,
  Lock,
  Cpu,
  Headset,
  Building2,
  Scale,
  Briefcase,
  Hammer,
} from "lucide-react";
import { TOOLS } from "@/lib/tools";

const stats = [
  { label: "Recuperación con citas", value: "100%", detail: "Cada respuesta enlaza a la fuente" },
  { label: "Cobertura corpus", value: "CDMX + Fed", detail: "Normativa pública y docs de despacho" },
  { label: "Velocidad de respuesta", value: "~2s", detail: "Consulta + generación con streaming" },
];

const platform = [
  {
    icon: <Bot className="h-5 w-5 text-accent" />,
    title: "Assistant",
    body: "Asistente personal entrenado en tus flujos: delega tareas complejas en lenguaje natural.",
    cta: "Explorar Assistant",
  },
  {
    icon: <FileSearch className="h-5 w-5 text-accent" />,
    title: "Knowledge",
    body: "Investigación rápida con citas verificables sobre derecho, regulación y fiscal.",
    cta: "Explorar Knowledge",
  },
  {
    icon: <ScrollText className="h-5 w-5 text-accent" />,
    title: "Vault",
    body: "Workspaces seguros para subir y analizar miles de documentos con IA generativa.",
    cta: "Explorar Vault",
  },
  {
    icon: <Workflow className="h-5 w-5 text-accent" />,
    title: "Workflows",
    body: "Agentes multi-modelo que entregan producto final para tareas repetitivas. Más en camino.",
    cta: "Explorar Workflows",
  },
];

const solutions = [
  {
    icon: <Building2 className="h-5 w-5 text-accent" />,
    title: "In-House",
    body: "Reduce trabajo operativo y libera tiempo para la estrategia del negocio.",
  },
  {
    icon: <Hammer className="h-5 w-5 text-accent" />,
    title: "Litigio",
    body: "Apoyo en escritos, revisión de precedentes y preparación de audiencias.",
  },
  {
    icon: <Briefcase className="h-5 w-5 text-accent" />,
    title: "Transaccional",
    body: "Diligencia, revisión contractual y resúmenes de riesgos más rápidos.",
  },
  {
    icon: <Scale className="h-5 w-5 text-accent" />,
    title: "Innovation / Legal Ops",
    body: "Prompts y datasets de la firma, controlados y medibles para mostrar impacto.",
  },
];

const testimonials = [
  {
    quote:
      "La IA generativa está cambiando la asesoría jurídica. Queremos liderar y mantener trazabilidad en cada respuesta.",
    name: "Líder de Innovación",
    role: "Firma AmLaw / LatAm",
  },
  {
    quote:
      "El tiempo de respuesta bajó drásticamente; ahora enfocamos a socios en estrategia, no en buscar documentos.",
    name: "GC",
    role: "Empresa multinacional",
  },
];

export default function Home() {
  return (
    <div className="relative mx-auto max-w-6xl px-6 pb-20">
      <div className="pointer-events-none absolute inset-0 opacity-70">
        <div className="absolute left-[-10%] top-0 h-80 w-80 rounded-full bg-accent/10 blur-[110px]" />
        <div className="absolute right-[-15%] top-24 h-96 w-96 rounded-full bg-accent-strong/10 blur-[140px]" />
      </div>

      <section className="grid gap-10 rounded-3xl border border-border/70 bg-surface/80 px-6 py-12 shadow-2xl shadow-black/30 md:grid-cols-[1.1fr,0.9fr] md:px-10">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
            <Sparkles className="h-4 w-4" />
            IA jurídica con trazabilidad
          </div>
          <h1 className="text-4xl font-semibold leading-tight md:text-5xl">
            Un asistente legal que busca, responde y redacta con citas verificables.
          </h1>
          <p className="max-w-2xl text-lg text-muted">
            Conecta tu repositorio jurídico a un panel único. Cada herramienta llama al backend correcto: búsqueda
            vectorial, Q&A con citas, resúmenes y redacción basada en plantillas.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/login"
              className="flex items-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong"
            >
              Entrar al workspace
              <ArrowRight className="h-4 w-4" />
            </Link>
            <div className="flex items-center gap-2 rounded-full border border-border px-4 py-3 text-sm text-muted">
              <Shield className="h-4 w-4 text-accent" />
              JWT planeado; demo segura hoy.
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="relative h-48 overflow-hidden rounded-2xl border border-border/70 bg-card/80">
            <Image
              src="https://images.unsplash.com/photo-1505664194779-8beaceb93744?auto=format&fit=crop&w=1400&q=80"
              alt="Escritorio de madera con libros y balanza"
              fill
              className="object-cover"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-br from-background/40 via-background/10 to-background/60" />
            <div className="relative flex h-full items-end justify-between p-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted">Contexto legal</p>
                <p className="text-sm font-semibold text-foreground">Corpus CDMX + Federal</p>
              </div>
              <span className="rounded-full border border-border bg-background/70 px-3 py-1 text-[11px] font-semibold text-muted">
                Fuentes abiertas
              </span>
            </div>
          </div>
          <div className="rounded-2xl border border-border/70 bg-card/80 p-5">
            <p className="text-sm font-semibold text-accent">Vista de herramientas</p>
            <ul className="mt-4 space-y-3 text-sm text-muted">
              {TOOLS.slice(0, 5).map((tool) => (
                <li
                  key={tool.id}
                  className="flex items-start justify-between rounded-xl border border-border/60 bg-background/40 px-4 py-3"
                >
                  <div>
                    <p className="text-base font-semibold text-foreground">{tool.name}</p>
                    <p className="text-xs text-muted">{tool.description}</p>
                  </div>
                  <span
                    className={
                      tool.status === "ready"
                        ? "rounded-full bg-accent/15 px-3 py-1 text-[11px] font-semibold text-accent-strong"
                        : "rounded-full bg-border/70 px-3 py-1 text-[11px] font-semibold text-muted"
                    }
                  >
                    {tool.status === "ready" ? "Disponible" : "Placeholder"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {stats.map((stat) => (
              <div key={stat.label} className="rounded-2xl border border-border/60 bg-card/70 p-4">
                <p className="text-xs uppercase tracking-wide text-muted">{stat.label}</p>
                <p className="mt-2 text-xl font-semibold text-foreground">{stat.value}</p>
                <p className="text-xs text-muted">{stat.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        id="platform"
        className="mt-14 grid gap-6 rounded-3xl border border-border/70 bg-surface/80 p-10 shadow-xl shadow-black/25 md:grid-cols-[1.1fr,0.9fr]"
      >
        <div className="space-y-4">
          <p className="text-sm uppercase tracking-wide text-muted">Panel unificado</p>
          <h2 className="text-3xl font-semibold">Una barra de herramientas, múltiples flujos.</h2>
          <p className="text-muted">
            El dashboard replica la experiencia de un chat experto pero con botones de herramientas a la derecha para
            cambiar de contexto: Búsqueda, Q&A, Resumen, Redacción, Case Builder.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            <Pill icon={<BookOpenCheck className="h-4 w-4" />} label="Citas obligatorias" />
            <Pill icon={<Bot className="h-4 w-4" />} label="Prompts listos por herramienta" />
            <Pill icon={<Clock3 className="h-4 w-4" />} label="Respuestas en ~2s" />
            <Pill icon={<Workflow className="h-4 w-4" />} label="Rutas de backend separadas" />
          </div>
          <div className="flex gap-3">
            <Link
              href="/dashboard"
              className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong"
            >
              Ver el panel
            </Link>
            <Link
              href="/login"
              className="rounded-full border border-border px-5 py-3 text-sm font-semibold text-foreground transition hover:border-accent hover:text-accent"
            >
              Solicitar demo
            </Link>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-card/70 p-6">
          <div className="absolute inset-0 bg-gradient-to-br from-accent/10 via-transparent to-accent-strong/10" />
          <div className="relative space-y-4">
            <div className="flex items-center justify-between rounded-xl border border-border/60 bg-background/60 px-4 py-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted">Chat</p>
                <p className="text-sm font-semibold text-foreground">Q&A con citas</p>
              </div>
              <span className="rounded-full bg-accent/15 px-3 py-1 text-[11px] font-semibold text-accent-strong">
                Disponible
              </span>
            </div>
            <div className="space-y-3 rounded-xl border border-border/60 bg-background/60 p-4 text-sm text-muted">
              <div className="self-start rounded-lg bg-card/80 p-3">
                ¿Qué requisitos aplican a licitaciones de obra pública en CDMX?
              </div>
              <div className="self-end rounded-lg bg-accent/15 p-3 text-foreground">
                La Ley de Obras Públicas y Servicios Relacionados con las Mismas (CDMX) establece requisitos de capacidad
                técnica y solvencia económica (Art. 28). Debes presentar garantías (Art. 48) y evidencia de experiencia
                previa (Art. 35).
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-background/60 p-4">
              <p className="text-xs uppercase tracking-wide text-muted">Herramientas</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                {TOOLS.slice(0, 6).map((tool) => (
                  <span
                    key={tool.id}
                    className="rounded-full border border-border bg-card/70 px-3 py-2 font-semibold text-foreground"
                  >
                    {tool.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="solutions"
        className="mt-14 rounded-3xl border border-border/70 bg-surface/70 p-8 shadow-xl shadow-black/20"
      >
        <p className="text-sm uppercase tracking-wide text-muted">Soluciones para equipos jurídicos</p>
        <h3 className="mt-2 text-2xl font-semibold">Adapta la IA a tu práctica.</h3>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          {solutions.map((solution) => (
            <div key={solution.title} className="rounded-2xl border border-border/60 bg-card/80 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background/60">
                {solution.icon}
              </div>
              <p className="mt-3 text-lg font-semibold text-foreground">{solution.title}</p>
              <p className="mt-2 text-sm text-muted">{solution.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-14 rounded-3xl border border-border/70 bg-surface/70 p-8 shadow-xl shadow-black/20">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-muted">Plataforma integrada</p>
            <h2 className="text-3xl font-semibold">Un stack de IA especializado para abogados.</h2>
            <p className="text-muted">
              Diseñado para firmas y equipos legales: asistentes, conocimiento con citas, vaults seguros y agentes
              multi-modelo.
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/dashboard"
              className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong"
            >
              Ver demo rápida
            </Link>
            <Link
              href="/login"
              className="rounded-full border border-border px-5 py-3 text-sm font-semibold text-foreground transition hover:border-accent hover:text-accent"
            >
              Solicitar implementación
            </Link>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {platform.map((item) => (
            <div key={item.title} className="rounded-2xl border border-border/60 bg-card/80 p-5">
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background/60">
                  {item.icon}
                </div>
                <span className="rounded-full bg-accent/15 px-3 py-1 text-[11px] font-semibold text-accent-strong">
                  Incluido
                </span>
              </div>
              <p className="mt-3 text-lg font-semibold text-foreground">{item.title}</p>
              <p className="mt-2 text-sm text-muted">{item.body}</p>
              <button className="mt-3 text-sm font-semibold text-accent hover:text-accent-strong">
                {item.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section
        id="impact"
        className="mt-14 grid gap-6 rounded-3xl border border-border/70 bg-surface/80 p-8 shadow-xl shadow-black/25 md:grid-cols-[1.2fr,0.8fr]"
      >
        <div className="space-y-3">
          <p className="text-sm uppercase tracking-wide text-muted">Impacto cuantificable</p>
          <h3 className="text-3xl font-semibold">Resultados visibles en semanas.</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <StatBig title="700+" body="Firmas y empresas líderes (referencias globales)" />
            <StatBig title="50%" body="AmLaw 100 adoptando IA con trazabilidad" />
            <StatBig title="74k+" body="Profesionales usando asistentes especializados" />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <ValuePill
              icon={<Lock className="h-4 w-4 text-accent" />}
              title="Seguridad enterprise"
              body="Sin entrenar modelos con tus datos; aislamiento de workspaces."
            />
            <ValuePill
              icon={<Cpu className="h-4 w-4 text-accent" />}
              title="Modelos de dominio"
              body="Modelos ajustados a lenguaje jurídico y fiscal, listos para producción."
            />
            <ValuePill
              icon={<Headset className="h-4 w-4 text-accent" />}
              title="Soporte 24/7"
              body="Acompañamiento para prompts, datasets y monitoreo."
            />
            <ValuePill
              icon={<ShieldCheck className="h-4 w-4 text-accent" />}
              title="Citas obligatorias"
              body="Cada respuesta entrega contexto y enlace a la fuente."
            />
          </div>
        </div>
        <div className="space-y-4 rounded-2xl border border-border/60 bg-card/80 p-6">
          <p className="text-sm uppercase tracking-wide text-muted">Testimonios</p>
          {testimonials.map((t) => (
            <div key={t.name} className="rounded-xl border border-border/60 bg-background/50 p-4">
              <p className="text-sm text-foreground leading-relaxed">“{t.quote}”</p>
              <p className="mt-2 text-xs font-semibold text-muted">
                {t.name} — {t.role}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-14 flex flex-col gap-4 rounded-3xl border border-border/70 bg-surface/70 p-8 text-center shadow-xl shadow-black/20">
        <p className="text-sm uppercase tracking-wide text-muted">Listo para producción</p>
        <h3 className="text-3xl font-semibold">Activa el flujo legal completo en un solo lugar.</h3>
        <p className="text-muted">
          Conecta endpoints existentes, añade JWT, y extiende las herramientas. Te acompañamos con prompts y datasets
          dedicados por flujo.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link
            href="/dashboard"
            className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-contrast transition hover:bg-accent-strong"
          >
            Probar panel ahora
          </Link>
          <Link
            href="/login"
            className="rounded-full border border-border px-6 py-3 text-sm font-semibold text-foreground transition hover:border-accent hover:text-accent"
          >
            Hablar con nosotros
          </Link>
        </div>
      </section>
    </div>
  );
}

function Pill({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-border/60 bg-background/60 px-3 py-2 text-xs font-semibold text-foreground">
      {icon}
      {label}
    </div>
  );
}

function ValuePill({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/50 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
        {icon}
        {title}
      </div>
      <p className="mt-1 text-xs text-muted">{body}</p>
    </div>
  );
}

function StatBig({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-border/60 bg-card/80 p-4">
      <p className="text-2xl font-semibold text-foreground">{title}</p>
      <p className="text-sm text-muted">{body}</p>
    </div>
  );
}
