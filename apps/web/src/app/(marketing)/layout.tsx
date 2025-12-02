import type { ReactNode } from "react";
import { SiteHeader } from "@/components/site-header";

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <SiteHeader />
      {children}
    </div>
  );
}
