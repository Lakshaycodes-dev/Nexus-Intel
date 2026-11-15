import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowUpRight, BadgeCheck, Radar, ShieldCheck } from "lucide-react";

import { Logo } from "@/components/logo";

const highlights = [
  {
    icon: Radar,
    title: "Continuous competitor scans",
    detail:
      "Monitor your industry rivals, track their digital footprint, and keep your entire watchlist updated in real-time.",
  },
  {
    icon: BadgeCheck,
    title: "Verified pricing bands",
    detail: "Every price traces back to a rendered page, with extraction provenance.",
  },
  {
    icon: ShieldCheck,
    title: "Private workspace",
    detail: "Your scans, reports and history stay scoped to your account.",
  },
];

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#F6F7FB]">
      <div
        aria-hidden
        className="pointer-events-none absolute -left-32 -top-32 h-[420px] w-[420px] rounded-full bg-indigo-200/40 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-40 -right-24 h-[460px] w-[460px] rounded-full bg-cyan-200/40 blur-3xl"
      />

      <div className="relative mx-auto grid min-h-screen w-full max-w-6xl items-center gap-12 px-4 py-10 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:px-8">
        <aside className="hidden lg:block">
          <Logo href="/" />
          <h1 className="mt-8 max-w-md text-[34px] font-semibold leading-[1.15] tracking-[-0.035em] text-ink">
            AI-powered competitive intelligence for modern enterprises.
          </h1>
          <p className="mt-3 max-w-md text-[13.5px] leading-relaxed text-slate-500">
            Track competitor strategies, pricing changes, and market trends across
            any sector that matters to your business.
          </p>

          <ul className="mt-8 space-y-4">
            {highlights.map(({ icon: Icon, title: itemTitle, detail }) => (
              <li key={itemTitle} className="flex gap-3">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-indigo-100 bg-indigo-50 text-indigo-600">
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-[12.5px] font-semibold text-slate-800">{itemTitle}</p>
                  <p className="mt-0.5 max-w-xs text-[11.5px] leading-relaxed text-slate-500">
                    {detail}
                  </p>
                </div>
              </li>
            ))}
          </ul>

          <Link
            href="/"
            className="mt-9 inline-flex items-center gap-1 text-[11.5px] font-semibold text-slate-500 transition hover:text-indigo-600"
          >
            Back to the site
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </aside>

        <main className="mx-auto w-full max-w-[430px]">
          <div className="mb-6 lg:hidden">
            <Logo href="/" />
          </div>

          <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-card sm:p-8">
            <h2 className="text-[22px] font-semibold tracking-[-0.03em] text-ink">{title}</h2>
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-slate-500">{subtitle}</p>
            <div className="mt-6">{children}</div>
          </div>

          {footer ? (
            <div className="mt-5 text-center text-[12px] text-slate-500">{footer}</div>
          ) : null}

          <p className="mt-6 text-center text-[10px] leading-relaxed text-slate-400">
            By continuing you agree to the Nexus-Intel terms of service and privacy
            policy.
          </p>
        </main>
      </div>
    </div>
  );
}
