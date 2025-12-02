"use client";

import { Toaster } from "sonner";
import type { ReactNode } from "react";

type ProvidersProps = {
  children: ReactNode;
};

export function Providers({ children }: ProvidersProps) {
  return (
    <>
      <Toaster richColors position="top-right" />
      {children}
    </>
  );
}
