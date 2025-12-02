import type { Metadata } from "next";
import { Playfair_Display, Source_Sans_3 } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const heading = Playfair_Display({
  variable: "--font-heading",
  subsets: ["latin"],
  display: "swap",
});

const body = Source_Sans_3({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://example.com"),
  title: {
    default: "LexToolkit | IA jurídica",
    template: "%s | LexToolkit",
  },
  description:
    "Asistente legal con búsqueda, Q&A con citas, resúmenes y redacción conectados a tu corpus. Pensado para despachos y equipos jurídicos.",
  openGraph: {
    title: "LexToolkit | IA jurídica con trazabilidad",
    description:
      "Búsqueda, Q&A, resúmenes y redacción con citas verificables. Plataforma para despachos y equipos jurídicos.",
    url: "https://example.com",
    siteName: "LexToolkit",
    locale: "es_MX",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LexToolkit | IA jurídica con trazabilidad",
    description:
      "Un panel unificado para búsqueda, Q&A, resúmenes y redacción con citas y seguridad.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${heading.variable} ${body.variable} bg-background text-foreground antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
