"use client";

import { useState } from "react";
import {
  Check,
  CheckCircle2,
  Sparkles,
  TableProperties,
  XCircle,
} from "lucide-react";
import type { CompetitorData } from "@/lib/mockData";

type BillingCycle = "monthly" | "annual";

interface ComparisonMatrixProps {
  data: CompetitorData;
}

function numericPrice(value: string): number {
  const parsed = Number(value.replace(/[^0-9.]/g, ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

export default function ComparisonMatrix({ data }: ComparisonMatrixProps) {
  const [billing, setBilling] = useState<BillingCycle>("monthly");

  const maxSavings = Math.max(
    0,
    ...data.pricing.map((tier) => {
      const monthly = numericPrice(tier.monthly);
      const annual = numericPrice(tier.annual);
      if (!monthly || !annual || annual >= monthly) return 0;
      return Math.round((1 - annual / monthly) * 100);
    }),
  );

  const nexusScore = data.capabilities.filter((item) => item.nexusIntel).length;
  const traditionalScore = data.capabilities.filter(
    (item) => item.traditionalScraper,
  ).length;
  const exclusiveSurfaces = data.capabilities.filter(
    (item) => item.nexusIntel && !item.traditionalScraper,
  ).length;

  return (
    <section className="glass-panel relative overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-400/50 to-transparent" />

      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/[0.06] p-5 sm:px-6">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-400/20 bg-indigo-500/[0.08]">
            <TableProperties className="h-4 w-4 text-indigo-300" />
          </span>
          <div>
            <h2 className="text-[15px] font-semibold tracking-tight text-white">
              Pricing &amp; capability matrix
            </h2>
            <p className="text-[11px] text-slate-500">
              Structured from live pricing pages and interactive DOM states.
            </p>
          </div>
        </div>

        <div
          className="inline-flex items-center rounded-lg border border-white/[0.08] bg-ink-950/70 p-0.5"
          role="group"
          aria-label="Billing cycle"
        >
          {(["monthly", "annual"] as const).map((cycle) => (
            <button
              key={cycle}
              type="button"
              onClick={() => setBilling(cycle)}
              aria-pressed={billing === cycle}
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium capitalize transition-all focus-ring ${
                billing === cycle
                  ? "bg-white/[0.09] text-white shadow-inner-line"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {cycle}
              {cycle === "annual" && maxSavings > 0 && (
                <span
                  className={`rounded px-1 py-px font-mono text-[9px] ${
                    billing === "annual"
                      ? "bg-emerald-400/15 text-emerald-300"
                      : "bg-white/[0.04] text-slate-500"
                  }`}
                >
                  −{maxSavings}%
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5 sm:px-6">
        <div className="grid gap-2.5 sm:grid-cols-3">
          {data.pricing.map((tier, index) => {
            const highlighted = index === 1;
            const monthly = numericPrice(tier.monthly);
            const annual = numericPrice(tier.annual);
            const savings =
              monthly && annual && annual < monthly
                ? Math.round((1 - annual / monthly) * 100)
                : 0;
            const price = billing === "monthly" ? tier.monthly : tier.annual;

            return (
              <article
                key={tier.tier}
                className={`relative overflow-hidden rounded-xl border p-4 transition-colors duration-300 ${
                  highlighted
                    ? "border-indigo-400/30 bg-gradient-to-b from-indigo-500/[0.12] to-indigo-500/[0.02]"
                    : "border-white/[0.07] bg-white/[0.02] hover:border-white/[0.13]"
                }`}
              >
                {highlighted && (
                  <div className="pointer-events-none absolute -right-10 -top-10 h-24 w-24 rounded-full bg-indigo-500/15 blur-2xl" />
                )}
                <div className="relative">
                  <div className="flex items-center justify-between">
                    <h3 className="text-[12.5px] font-semibold text-slate-200">
                      {tier.tier}
                    </h3>
                    <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-slate-600">
                      Tier 0{index + 1}
                    </span>
                  </div>

                  <div className="mt-3 flex items-baseline gap-1">
                    <span className="text-[26px] font-semibold leading-none tracking-tight text-white">
                      {price}
                    </span>
                    <span className="text-[10px] text-slate-500">/mo</span>
                  </div>
                  <div className="mt-1 h-4 text-[9.5px]">
                    {billing === "annual" ? (
                      <span className="text-emerald-300/80">
                        {monthly === 0 && annual === 0
                          ? "Always free"
                          : `Billed annually · save ${savings}%`}
                      </span>
                    ) : (
                      <span className="text-slate-600">Billed month to month</span>
                    )}
                  </div>

                  <ul className="mt-3 space-y-1.5 border-t border-white/[0.06] pt-3">
                    {tier.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-1.5 text-[10.5px] leading-snug text-slate-400"
                      >
                        <Check
                          className={`mt-px h-3 w-3 shrink-0 ${
                            highlighted ? "text-indigo-300" : "text-slate-500"
                          }`}
                          strokeWidth={2.5}
                        />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            );
          })}
        </div>

        <div className="mt-6">
          <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
            <h3 className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-200">
              <Sparkles className="h-3.5 w-3.5 text-indigo-300" />
              Extraction coverage
            </h3>
            <div className="flex items-center gap-1.5">
              <span className="chip border-emerald-400/20 bg-emerald-500/[0.06] py-0.5 text-[9.5px] text-emerald-300">
                Nexus {nexusScore}/{data.capabilities.length}
              </span>
              <span className="chip border-rose-400/20 bg-rose-500/[0.06] py-0.5 text-[9.5px] text-rose-300">
                Legacy {traditionalScore}/{data.capabilities.length}
              </span>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-white/[0.07]">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-white/[0.07] bg-white/[0.025]">
                  <th className="px-4 py-2.5 text-[10px] font-medium uppercase tracking-[0.12em] text-slate-500">
                    Capability
                  </th>
                  <th className="w-[28%] bg-indigo-500/[0.06] px-2 py-2.5 text-center text-[10px] font-semibold uppercase tracking-[0.1em] text-indigo-200">
                    Nexus Intel
                  </th>
                  <th className="w-[28%] px-2 py-2.5 text-center text-[10px] font-medium uppercase tracking-[0.1em] text-slate-500">
                    Traditional scraper
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.capabilities.map((capability) => (
                  <tr
                    key={capability.name}
                    className="border-b border-white/[0.05] transition-colors last:border-b-0 hover:bg-white/[0.02]"
                  >
                    <td className="px-4 py-2.5 text-[11.5px] font-medium text-slate-300">
                      {capability.name}
                    </td>
                    <td className="bg-indigo-500/[0.04] px-2 py-2.5">
                      <span className="flex items-center justify-center">
                        {capability.nexusIntel ? (
                          <CheckCircle2
                            className="h-4 w-4 text-emerald-400"
                            aria-label="Captured"
                          />
                        ) : (
                          <XCircle
                            className="h-4 w-4 text-rose-400/80"
                            aria-label="Missed"
                          />
                        )}
                      </span>
                    </td>
                    <td className="px-2 py-2.5">
                      <span className="flex items-center justify-center">
                        {capability.traditionalScraper ? (
                          <CheckCircle2
                            className="h-4 w-4 text-emerald-400/70"
                            aria-label="Captured"
                          />
                        ) : (
                          <XCircle
                            className="h-4 w-4 text-rose-400/80"
                            aria-label="Missed"
                          />
                        )}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-3 flex items-start gap-1.5 text-[10.5px] leading-relaxed text-slate-500">
            <Sparkles className="mt-px h-3 w-3 shrink-0 text-indigo-300/80" />
            Nexus Intel unlocks{" "}
            <span className="font-medium text-slate-300">
              {exclusiveSurfaces} surfaces
            </span>{" "}
            that static scrapers cannot render — hidden toggles, JS content and
            off-site sentiment.
          </p>
        </div>
      </div>
    </section>
  );
}
