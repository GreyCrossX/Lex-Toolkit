"use client";
import { ArrowUpRight, CircleDot, ShieldCheck } from "lucide-react";
import type { Tool } from "@/lib/tools";
import clsx from "clsx";

type ToolCardProps = {
  tool: Tool;
  onSelect: (tool: Tool) => void;
};

export function ToolCard({ tool, onSelect }: ToolCardProps) {
  return (
    <button
      onClick={() => onSelect(tool)}
      className="group flex flex-col rounded-2xl border border-border/70 bg-card/80 p-4 text-left transition hover:-translate-y-0.5 hover:border-accent hover:bg-card/100"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-muted">
          <CircleDot className="h-4 w-4 text-accent" />
          <span>{tool.category}</span>
        </div>
        <StatusPill status={tool.status} />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <h3 className="text-lg font-semibold text-foreground">{tool.name}</h3>
        <ArrowUpRight className="h-4 w-4 text-accent transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      </div>

      <p className="mt-2 text-sm leading-relaxed text-muted">{tool.description}</p>

      <div className="mt-4 flex items-center gap-2 text-xs text-muted">
        <ShieldCheck className="h-4 w-4 text-accent" />
        <span>{tool.cta ?? "Herramienta no disponible (placeholder)"}</span>
      </div>
    </button>
  );
}

function StatusPill({ status }: { status: Tool["status"] }) {
  const label = status === "ready" ? "Disponible" : "Próximamente";
  return (
    <span
      className={clsx(
        "rounded-full px-3 py-1 text-xs font-medium",
        status === "ready"
          ? "bg-accent/20 text-foreground border border-accent/40"
          : "bg-border/60 text-muted border border-border"
      )}
    >
      {label}
    </span>
  );
}
