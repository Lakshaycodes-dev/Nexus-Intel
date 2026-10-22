"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Gauge, Plug, ShieldCheck, X } from "lucide-react";
import type { FeatureGroup } from "@/lib/types";
import { cn } from "@/lib/utils";

const categoryStyle = [
  {
    icon: ShieldCheck,
    tile: "border-indigo-100 bg-indigo-50 text-indigo-600",
  },
  {
    icon: Plug,
    tile: "border-cyan-100 bg-cyan-50 text-cyan-600",
  },
  {
    icon: Gauge,
    tile: "border-emerald-100 bg-emerald-50 text-emerald-600",
  },
];

export function FeatureAccordions({ groups }: { groups: FeatureGroup[] }) {
  const [openGroups, setOpenGroups] = useState<string[]>([groups[0]?.category ?? ""]);
  const allOpen = openGroups.length === groups.length;

  function toggle(category: string) {
    setOpenGroups((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category],
    );
  }

  function toggleAll() {
    setOpenGroups(allOpen ? [] : groups.map((group) => group.category));
  }

  return (
    <section className="print-avoid-break overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
      <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-ink">
            Feature comparison
          </h2>
          <p className="mt-1 text-[11px] text-slate-500">
            {groups.length} categories ·{" "}
            {groups.reduce((total, group) => total + group.features.length, 0)} capabilities
            resolved
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden items-center gap-3 text-[9px] text-slate-400 sm:flex">
            <span className="inline-flex items-center gap-1">
              <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                <Check className="h-2 w-2" strokeWidth={3} />
              </span>
              Included
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                <X className="h-2 w-2" strokeWidth={3} />
              </span>
              Not available
            </span>
          </div>
          <button
            type="button"
            onClick={toggleAll}
            className="text-[10px] font-semibold text-indigo-600 transition hover:text-indigo-800"
          >
            {allOpen ? "Collapse all" : "Expand all"}
          </button>
        </div>
      </div>

      <div className="divide-y divide-slate-100">
        {groups.map((group, groupIndex) => {
          const style = categoryStyle[groupIndex % categoryStyle.length];
          const Icon = style.icon;
          const open = openGroups.includes(group.category);
          const included = group.features.filter((feature) => feature.included).length;
          const panelId = `feature-panel-${groupIndex}`;

          return (
            <div key={group.category}>
              <button
                type="button"
                onClick={() => toggle(group.category)}
                aria-expanded={open}
                aria-controls={panelId}
                className="flex w-full items-center gap-3.5 px-5 py-4 text-left transition-colors hover:bg-slate-50/60 sm:px-6"
              >
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
                    style.tile,
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span className="text-[12px] font-semibold text-slate-800">
                      {group.category}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[8px] font-medium text-slate-400">
                      {included}/{group.features.length}
                    </span>
                  </span>
                  <span className="mt-0.5 block truncate text-[10px] text-slate-400">
                    {group.description}
                  </span>
                </span>
                <span
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-400 transition-transform duration-200",
                    open && "rotate-180",
                  )}
                >
                  <ChevronDown className="h-3 w-3" />
                </span>
              </button>

              <AnimatePresence initial={false}>
                {open ? (
                  <motion.div
                    id={panelId}
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.22, ease: "easeInOut" }}
                    className="overflow-hidden"
                  >
                    <div className="px-5 pb-4 sm:px-6">
                      <div className="overflow-hidden rounded-lg border border-slate-100">
                        {group.features.map((feature, index) => (
                          <div
                            key={feature.name}
                            className={cn(
                              "flex items-center gap-3 px-3.5 py-2.5",
                              index !== group.features.length - 1 &&
                                "border-b border-slate-100",
                            )}
                          >
                            <span
                              className={cn(
                                "flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                                feature.included
                                  ? "bg-emerald-50 text-emerald-600"
                                  : "bg-slate-50 text-slate-300",
                              )}
                            >
                              {feature.included ? (
                                <Check className="h-2.5 w-2.5" strokeWidth={3} />
                              ) : (
                                <X className="h-2.5 w-2.5" strokeWidth={2.5} />
                              )}
                            </span>
                            <span
                              className={cn(
                                "min-w-0 flex-1 text-[10.5px]",
                                feature.included ? "text-slate-600" : "text-slate-400",
                              )}
                            >
                              {feature.name}
                            </span>
                            <span className="hidden text-right text-[9px] text-slate-400 sm:block">
                              {feature.detail}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}
