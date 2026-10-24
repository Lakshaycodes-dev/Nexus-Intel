"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Check, ExternalLink, ShieldCheck } from "lucide-react";
import type { Competitor } from "@/lib/types";
import { cn } from "@/lib/utils";

type Billing = "monthly" | "annual";

export function PricingMatrix({ competitor }: { competitor: Competitor }) {
  const [billing, setBilling] = useState<Billing>("monthly");

  return (
    <section className="print-avoid-break overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
      <div className="flex flex-col gap-4 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[15px] font-semibold tracking-tight text-ink">Pricing matrix</h2>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-[0.1em] text-slate-400">
              USD
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            Every public tier, normalized across billing cycles.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="flex items-center gap-1 text-[9px] text-slate-400">
            <ShieldCheck className="h-3 w-3 text-emerald-500" />
            Verified {competitor.lastScan}
          </span>
          <div className="flex items-center rounded-full border border-slate-200 bg-slate-50 p-0.5">
            <button
              type="button"
              onClick={() => setBilling("monthly")}
              aria-pressed={billing === "monthly"}
              className={cn(
                "rounded-full px-3 py-1.5 text-[10px] font-semibold transition",
                billing === "monthly"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700",
              )}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={() => setBilling("annual")}
              aria-pressed={billing === "annual"}
              className={cn(
                "flex items-center gap-1 rounded-full px-3 py-1.5 text-[10px] font-semibold transition",
                billing === "annual"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700",
              )}
            >
              Annual
              <span className="rounded-full bg-emerald-50 px-1 py-0.5 text-[7px] font-semibold text-emerald-600">
                −20%
              </span>
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-3 p-4 sm:p-5 lg:grid-cols-3">
        {competitor.pricing.map((tier) => {
          const price = billing === "annual" ? tier.annualMonthly : tier.monthly;
          const savings = (tier.monthly - tier.annualMonthly) * 12;

          return (
            <div
              key={tier.name}
              className={cn(
                "relative flex flex-col rounded-xl border p-4 transition-colors",
                tier.highlighted
                  ? "border-indigo-200 bg-gradient-to-b from-indigo-50/60 via-white to-white shadow-[0_12px_32px_-18px_rgba(79,70,229,0.35)]"
                  : "border-slate-200 bg-white",
              )}
            >
              {tier.highlighted ? (
                <span className="absolute right-3 top-3 rounded-full border border-indigo-100 bg-white px-2 py-0.5 text-[7.5px] font-semibold uppercase tracking-[0.1em] text-indigo-600">
                  {tier.badge}
                </span>
              ) : null}

              <p className="text-[12px] font-semibold text-slate-900">{tier.name}</p>
              <p className="mt-1 min-h-[30px] max-w-[190px] text-[10px] leading-relaxed text-slate-400">
                {tier.description}
              </p>

              <div className="mt-3 flex items-end gap-1">
                <span className="text-[13px] font-medium text-slate-400">$</span>
                <motion.span
                  key={`${tier.name}-${billing}`}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.18 }}
                  className="text-[30px] font-semibold leading-none tracking-[-0.04em] text-ink tabular"
                >
                  {price}
                </motion.span>
                <span className="pb-0.5 text-[10px] text-slate-400">/ mo</span>
              </div>
              <p className="mt-1.5 text-[9px] text-slate-400">
                {billing === "annual" ? (
                  <>
                    ${price * 12} billed annually ·{" "}
                    <span className="font-medium text-emerald-600">save ${savings}/yr</span>
                  </>
                ) : (
                  "Billed monthly · cancel anytime"
                )}
              </p>

              <div className="mt-4 space-y-2 border-t border-slate-100 pt-3.5">
                {tier.features.map((feature) => (
                  <div key={feature} className="flex items-start gap-2">
                    <span className="mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                      <Check className="h-2 w-2" strokeWidth={3} />
                    </span>
                    <span className="text-[10px] leading-relaxed text-slate-500">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col gap-2 border-t border-slate-100 bg-slate-50/50 px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <span className="text-[9px] text-slate-400">
          Captured from public pricing · {competitor.domain}/pricing
        </span>
        <a
          href={`https://${competitor.domain}/pricing`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-[9px] font-semibold text-slate-500 transition hover:text-indigo-600"
        >
          View source
          <ExternalLink className="h-2.5 w-2.5" />
        </a>
      </div>
    </section>
  );
}
