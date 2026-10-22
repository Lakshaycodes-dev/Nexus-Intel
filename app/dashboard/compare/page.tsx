import type { Metadata } from "next";
import { ArrowLeftRight, RefreshCw } from "lucide-react";
import { CompareWorkspace } from "@/components/dashboard/compare-workspace";

export const metadata: Metadata = {
  title: "Comparison Matrix",
  description:
    "Compare pricing, features, security, integrations, and support across your market.",
};

export default function ComparePage() {
  return (
    <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-100 bg-indigo-50 px-2 py-1 text-[8px] font-semibold uppercase tracking-[0.12em] text-indigo-700">
              <ArrowLeftRight className="h-2.5 w-2.5" />
              Comparison matrix
            </span>
            <span className="text-[10px] text-slate-400">Updated 8 minutes ago</span>
          </div>
          <h1 className="mt-3 text-[28px] font-semibold tracking-[-0.035em] text-ink sm:text-[32px]">
            The market, side by side.
          </h1>
          <p className="mt-1.5 max-w-xl text-[12.5px] leading-relaxed text-slate-500">
            Evaluate pricing, packaging, and platform depth across the competitors that
            matter most. Every cell is tied to a live source.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-[10px] font-medium text-slate-500 shadow-sm">
            <RefreshCw className="h-3 w-3 text-emerald-500" />
            8 competitors monitored
          </span>
          <span className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-[10px] font-medium text-slate-500 shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            16 data dimensions
          </span>
        </div>
      </header>

      <div className="mt-6">
        <CompareWorkspace />
      </div>
    </div>
  );
}
