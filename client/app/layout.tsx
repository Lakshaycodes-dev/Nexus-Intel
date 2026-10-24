import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "NEXUS INTEL — Autonomous Market & Competitor Intelligence",
    template: "%s · NEXUS INTEL",
  },
  description:
    "One missed price change can cost you a deal. Your competitors never stop moving. Now neither do you.",
  metadataBase: new URL("https://nexusintel.ai"),
  openGraph: {
    title: "NEXUS INTEL — Autonomous Market & Competitor Intelligence",
    description:
      "Continuous competitor monitoring, structured pricing matrices, and executive-ready market briefs.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#F8FAFC",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen bg-slate-50 font-sans text-slate-700 antialiased">
        {children}
      </body>
    </html>
  );
}
