import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nexus Intel — Autonomous Market & Competitor Intelligence",
  description:
    "Nexus Intel deploys autonomous web agents to capture competitor pricing, hidden feature toggles, and off-site sentiment — structured, deterministic, and fast.",
  applicationName: "Nexus Intel",
  keywords: [
    "competitor intelligence",
    "market intelligence",
    "autonomous agents",
    "TinyFish",
    "pricing intelligence",
  ],
  authors: [{ name: "Nexus Intel" }],
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#04060d",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen font-sans text-slate-200 antialiased">
        {children}
      </body>
    </html>
  );
}
