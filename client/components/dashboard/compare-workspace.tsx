"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDownUp,
  Check,
  ChevronDown,
  Clock3,
  Plus,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Trophy,
  Users,
  X,
} from "lucide-react";
import { competitors, myProduct } from "@/lib/data";
import type { Competitor } from "@/lib/types";
import { cn, formatCurrency } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type Direction = "lower" | "higher" | "boolean" | "none";

interface CellValue {
  display: string;
  raw?: string | number | boolean;
}

interface CompareRow {
  id: string;
  group: string;
  label: string;
  helper: string;
  mine: CellValue;
  get: (competitor: Competitor) => CellValue;
  direction: Direction;
}

function refreshLabel(minutes: number) {
  if (minutes < 60) return `${minutes} min`;
  if (minutes % 60 === 0) return `${minutes / 60}h`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

const rows: CompareRow[] = [
  {
    id: "starting",
    group: "Commercial",
    label: "Starting price",
    helper: "Lowest paid plan",
    mine: { display: formatCurrency(myProduct.startingPrice), raw: myProduct.startingPrice },
    get: (c) => ({ display: formatCurrency(c.startingPrice), raw: c.startingPrice }),
    direction: "lower",
  },
  {
    id: "pro",
    group: "Commercial",
    label: "Pro tier",
    helper: "Monthly billing",
    mine: { display: formatCurrency(myProduct.proPrice), raw: myProduct.proPrice },
    get: (c) => ({ display: formatCurrency(c.proPrice), raw: c.proPrice }),
    direction: "lower",
  },
  {
    id: "trial",
    group: "Commercial",
    label: "Free trial",
    helper: "Self-serve access",
    mine: {
      display: `${myProduct.comparison.freeTrialDays} days`,
      raw: myProduct.comparison.freeTrialDays,
    },
    get: (c) => ({
      display: `${c.comparison.freeTrialDays} days`,
      raw: c.comparison.freeTrialDays,
    }),
    direction: "higher",
  },
  {
    id: "refresh",
    group: "Monitoring",
    label: "Refresh cadence",
    helper: "Fastest paid cadence",
    mine: {
      display: refreshLabel(myProduct.comparison.refreshMinutes),
      raw: myProduct.comparison.refreshMinutes,
    },
    get: (c) => ({
      display: refreshLabel(c.comparison.refreshMinutes),
      raw: c.comparison.refreshMinutes,
    }),
    direction: "lower",
  },
  {
    id: "coverage",
    group: "Monitoring",
    label: "Off-site coverage",
    helper: "Where signals are found",
    mine: { display: myProduct.comparison.coverage },
    get: (c) => ({ display: c.comparison.coverage }),
    direction: "none",
  },
  {
    id: "storage",
    group: "Monitoring",
    label: "Snapshot storage",
    helper: "Intelligence retention",
    mine: {
      display: `${myProduct.comparison.retentionMonths} months`,
      raw: myProduct.comparison.retentionMonths,
    },
    get: (c) => ({
      display: `${c.comparison.retentionMonths} months`,
      raw: c.comparison.retentionMonths,
    }),
    direction: "higher",
  },
  {
    id: "sso",
    group: "Security",
    label: "SAML single sign-on",
    helper: "Enterprise identity",
    mine: { display: "Included", raw: myProduct.comparison.sso },
    get: (c) => ({ display: c.comparison.sso ? "Included" : "Not included", raw: c.comparison.sso }),
    direction: "boolean",
  },
  {
    id: "soc2",
    group: "Security",
    label: "SOC 2 Type II",
    helper: "Independent audit",
    mine: { display: "Certified", raw: myProduct.comparison.soc2 },
    get: (c) => ({ display: c.comparison.soc2 ? "Certified" : "Not certified", raw: c.comparison.soc2 }),
    direction: "boolean",
  },
  {
    id: "audit",
    group: "Security",
    label: "Audit logs",
    helper: "Change-level history",
    mine: { display: "Included", raw: myProduct.comparison.auditLogs },
    get: (c) => ({
      display: c.comparison.auditLogs ? "Included" : "Enterprise only",
      raw: c.comparison.auditLogs,
    }),
    direction: "boolean",
  },
  {
    id: "slack",
    group: "Integrations",
    label: "Slack & Teams",
    helper: "Team alert routing",
    mine: { display: "Included", raw: myProduct.comparison.slack },
    get: (c) => ({ display: c.comparison.slack ? "Included" : "Email only", raw: c.comparison.slack }),
    direction: "boolean",
  },
  {
    id: "crm",
    group: "Integrations",
    label: "CRM sync",
    helper: "Native connections",
    mine: { display: myProduct.comparison.crm },
    get: (c) => ({ display: c.comparison.crm }),
    direction: "none",
  },
  {
    id: "api",
    group: "Integrations",
    label: "REST API",
    helper: "Programmatic access",
    mine: { display: "Included", raw: myProduct.comparison.api },
    get: (c) => ({ display: c.comparison.api ? "Included" : "Not available", raw: c.comparison.api }),
    direction: "boolean",
  },
  {
    id: "webhooks",
    group: "Integrations",
    label: "Webhooks",
    helper: "Real-time delivery",
    mine: { display: "Included", raw: myProduct.comparison.webhooks },
    get: (c) => ({
      display: c.comparison.webhooks ? "Included" : "Not available",
      raw: c.comparison.webhooks,
    }),
    direction: "boolean",
  },
  {
    id: "sla",
    group: "Support",
    label: "P1 response SLA",
    helper: "Critical issues",
    mine: { display: myProduct.comparison.p1Response, raw: 4 },
    get: (c) => ({
      display: c.comparison.p1Response,
      raw: Number.parseFloat(c.comparison.p1Response),
    }),
    direction: "lower",
  },
  {
    id: "csm",
    group: "Support",
    label: "Dedicated CSM",
    helper: "Named success lead",
    mine: { display: "Included", raw: myProduct.comparison.dedicatedCsm },
    get: (c) => ({ display: c.comparison.dedicatedCsm ? "Included" : "Not included", raw: c.comparison.dedicatedCsm }),
    direction: "boolean",
  },
  {
    id: "onboarding",
    group: "Support",
    label: "Onboarding",
    helper: "Time-to-value",
    mine: { display: myProduct.comparison.onboarding },
    get: (c) => ({ display: c.comparison.onboarding }),
    direction: "none",
  },
];

function judge(row: CompareRow, mine: CellValue, other: CellValue) {
  if (row.direction === "none") return "neutral" as const;

  if (row.direction === "boolean") {
    if (mine.raw === true && other.raw === false) return "mine" as const;
    if (mine.raw === false && other.raw === true) return "other" as const;
    return "neutral" as const;
  }

  if (typeof mine.raw !== "number" || typeof other.raw !== "number") {
    return "neutral" as const;
  }
  if (mine.raw === other.raw) return "neutral" as const;

  const mineWins =
    row.direction === "lower" ? mine.raw < other.raw : mine.raw > other.raw;
  return mineWins ? ("mine" as const) : ("other" as const);
}

function ValueCell({
  value,
  outcome,
  emphasis = false,
}: {
  value: CellValue;
  outcome: "mine" | "other" | "neutral";
  emphasis?: boolean;
}) {
  if (typeof value.raw === "boolean") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 text-[10px]",
          value.raw
            ? "text-slate-700"
            : outcome === "other"
              ? "text-amber-700"
              : "text-slate-400",
        )}
      >
        <span
          className={cn(
            "flex h-5 w-5 items-center justify-center rounded-full",
            value.raw
              ? outcome === "other"
                ? "bg-amber-50 text-amber-600"
                : "bg-emerald-50 text-emerald-600"
              : "bg-slate-50 text-slate-300",
          )}
        >
          {value.raw ? (
            <Check className="h-2.5 w-2.5" strokeWidth={3} />
          ) : (
            <X className="h-2.5 w-2.5" strokeWidth={2.5} />
          )}
        </span>
        <span className="hidden sm:inline">{value.display}</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "text-[10.5px]",
        emphasis ? "font-semibold text-slate-800" : "text-slate-600",
        outcome === "other" && !emphasis && "font-medium text-amber-700",
      )}
    >
      {value.display}
    </span>
  );
}

const initialSelection = ["trackline", "compass-hq", "signalcraft"];

export function CompareWorkspace() {
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSelection);
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pickerOpen) return;

    function onPointerDown(event: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setPickerOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setPickerOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [pickerOpen]);

  const selected = useMemo(
    () =>
      selectedIds.flatMap((id) => {
        const competitor = competitors.find((item) => item.id === id);
        return competitor ? [competitor] : [];
      }),
    [selectedIds],
  );

  const groups = useMemo(
    () => Array.from(new Set(rows.map((row) => row.group))),
    [],
  );

  const leadCount = useMemo(
    () =>
      rows.filter((row) =>
        selected.some((competitor) => judge(row, row.mine, row.get(competitor)) === "mine"),
      ).length,
    [selected],
  );

  const chartData = useMemo(
    () => [
      { name: "Nexus Intel", starting: myProduct.startingPrice, pro: myProduct.proPrice },
      ...selected.map((competitor) => ({
        name: competitor.name,
        starting: competitor.startingPrice,
        pro: competitor.proPrice,
      })),
    ],
    [selected],
  );

  const allProducts = useMemo(
    () => [
      { name: "Nexus Intel", starting: myProduct.startingPrice, pro: myProduct.proPrice },
      ...selected.map((competitor) => ({
        name: competitor.name,
        starting: competitor.startingPrice,
        pro: competitor.proPrice,
      })),
    ],
    [selected],
  );

  const lowestEntry = allProducts.reduce((lowest, product) =>
    product.starting < lowest.starting ? product : lowest,
  );
  const highestPro = allProducts.reduce((highest, product) =>
    product.pro > highest.pro ? product : highest,
  );
  const proSpread = highestPro.pro - lowestEntry.starting;

  function toggleCompetitor(id: string) {
    setSelectedIds((current) => {
      if (current.includes(id)) {
        return current.filter((item) => item !== id);
      }
      if (current.length >= 4) return current;
      return [...current, id];
    });
  }

  const atLimit = selectedIds.length >= 4;

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-card sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[14px] font-semibold tracking-tight text-ink">
                Comparison set
              </h2>
              <Badge variant="brand" className="text-[8px]">
                {selected.length + 1} / 5 products
              </Badge>
            </div>
            <p className="mt-1 text-[10.5px] text-slate-500">
              Select up to four competitors to compare against your product.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setSelectedIds(initialSelection);
                setPickerOpen(false);
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-[10px] font-medium text-slate-500 shadow-sm transition hover:border-slate-300 hover:text-slate-700"
            >
              <RotateCcw className="h-3 w-3" />
              Reset
            </button>
            <div className="relative" ref={pickerRef}>
              <button
                type="button"
                onClick={() => setPickerOpen((value) => !value)}
                aria-expanded={pickerOpen}
                aria-haspopup="listbox"
                className="inline-flex h-9 items-center gap-2 rounded-lg bg-slate-900 px-3.5 text-[10px] font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                <Users className="h-3.5 w-3.5" />
                Select competitors
                <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-white/15 px-1 text-[8px]">
                  {selected.length}
                </span>
                <ChevronDown
                  className={cn("h-3 w-3 transition-transform", pickerOpen && "rotate-180")}
                />
              </button>

              <AnimatePresence>
                {pickerOpen ? (
                  <motion.div
                    initial={{ opacity: 0, y: -6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.98 }}
                    transition={{ duration: 0.15 }}
                    role="listbox"
                    aria-label="Select competitors"
                    className="absolute right-0 z-30 mt-2 w-[314px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl"
                  >
                    <div className="flex items-center justify-between border-b border-slate-100 px-3.5 py-2.5">
                      <span className="text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                        Your watchlist
                      </span>
                      <span className="text-[8px] text-slate-400">Select up to 4</span>
                    </div>
                    <div className="max-h-[310px] overflow-y-auto p-1.5">
                      {competitors.map((competitor) => {
                        const isSelected = selectedIds.includes(competitor.id);
                        const disabled = !isSelected && atLimit;
                        return (
                          <button
                            key={competitor.id}
                            type="button"
                            role="option"
                            aria-selected={isSelected}
                            disabled={disabled}
                            onClick={() => toggleCompetitor(competitor.id)}
                            className={cn(
                              "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition",
                              isSelected ? "bg-indigo-50/70" : "hover:bg-slate-50",
                              disabled && "cursor-not-allowed opacity-40",
                            )}
                          >
                            <span
                              className={cn(
                                "flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-gradient-to-br text-[7px] font-semibold text-white",
                                competitor.accent.gradient,
                              )}
                            >
                              {competitor.monogram}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-[10.5px] font-medium text-slate-700">
                                {competitor.name}
                              </span>
                              <span className="block truncate font-mono text-[8px] text-slate-400">
                                {competitor.domain}
                              </span>
                            </span>
                            <span
                              className={cn(
                                "flex h-4 w-4 items-center justify-center rounded border",
                                isSelected
                                  ? "border-indigo-500 bg-indigo-500 text-white"
                                  : "border-slate-300 bg-white",
                              )}
                            >
                              {isSelected ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : null}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                    <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/60 px-3.5 py-2.5">
                      <button
                        type="button"
                        onClick={() => setSelectedIds([])}
                        className="text-[9px] font-medium text-slate-400 transition hover:text-slate-700"
                      >
                        Clear selection
                      </button>
                      <button
                        type="button"
                        onClick={() => setPickerOpen(false)}
                        className="rounded-md bg-white px-2.5 py-1 text-[9px] font-semibold text-slate-600 shadow-sm ring-1 ring-slate-200"
                      >
                        Done
                      </button>
                    </div>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3.5">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 py-1 pl-1 pr-2.5 text-[9px] font-semibold text-indigo-700">
            <Image
              src="/nexus-intel-mark.png"
              alt=""
              width={270}
              height={270}
              className="h-4 w-4 rounded-full object-contain"
            />
            Nexus Intel
            <span className="rounded bg-white px-1 py-0.5 text-[7px] font-medium text-indigo-500">
              You
            </span>
          </span>
          {selected.map((competitor) => (
            <span
              key={competitor.id}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white py-1 pl-1 pr-1.5 text-[9px] font-medium text-slate-600"
            >
              <span
                className={cn(
                  "flex h-4 w-4 items-center justify-center rounded-full bg-gradient-to-br text-[6px] font-semibold text-white",
                  competitor.accent.gradient,
                )}
              >
                {competitor.monogram}
              </span>
              {competitor.name}
              <button
                type="button"
                onClick={() => toggleCompetitor(competitor.id)}
                aria-label={`Remove ${competitor.name}`}
                className="flex h-4 w-4 items-center justify-center rounded-full text-slate-300 transition hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </span>
          ))}
          {selected.length < 4 ? (
            <button
              type="button"
              onClick={() => setPickerOpen(true)}
              className="inline-flex items-center gap-1 rounded-full border border-dashed border-slate-300 px-2.5 py-1 text-[9px] font-medium text-slate-400 transition hover:border-indigo-300 hover:text-indigo-600"
            >
              <Plus className="h-2.5 w-2.5" />
              Add competitor
            </button>
          ) : null}
        </div>
      </section>

      <section className="print-avoid-break overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
        <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <h2 className="text-[15px] font-semibold tracking-tight text-ink">
              Feature & commercial matrix
            </h2>
            <p className="mt-1 text-[10.5px] text-slate-500">
              {rows.length} dimensions across pricing, security, integrations, and support.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1.5 text-[8px] text-slate-400">
              <span className="h-2 w-2 rounded-sm bg-emerald-100 ring-1 ring-emerald-200" />
              Nexus advantage
            </span>
            <span className="flex items-center gap-1.5 text-[8px] text-slate-400">
              <span className="h-2 w-2 rounded-sm bg-amber-100 ring-1 ring-amber-200" />
              Competitor advantage
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-100 bg-emerald-50 px-2 py-1 text-[8px] font-semibold text-emerald-700">
              <Trophy className="h-2.5 w-2.5" />
              {leadCount} / {rows.length} leads
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70">
                <th className="sticky left-0 z-20 w-[210px] bg-slate-50/95 px-5 py-3 text-[8px] font-semibold uppercase tracking-[0.12em] text-slate-400 backdrop-blur">
                  Capability
                </th>
                <th className="min-w-[150px] border-l border-indigo-100 bg-indigo-50/70 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Image
                      src="/nexus-intel-mark.png"
                      alt=""
                      width={270}
                      height={270}
                      className="h-6 w-6 rounded-md object-contain"
                    />
                    <div>
                      <p className="text-[9px] font-semibold text-indigo-800">Nexus Intel</p>
                      <p className="text-[7px] text-indigo-400">Your product</p>
                    </div>
                  </div>
                </th>
                {selected.map((competitor) => (
                  <th
                    key={competitor.id}
                    className="min-w-[138px] border-l border-slate-100 px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br text-[7px] font-semibold text-white",
                          competitor.accent.gradient,
                        )}
                      >
                        {competitor.monogram}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-[9px] font-semibold text-slate-700">
                          {competitor.name}
                        </p>
                        <p className="truncate text-[7px] text-slate-400">{competitor.domain}</p>
                      </div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <Fragment key={group}>
                  <tr>
                    <td
                      colSpan={selected.length + 2}
                      className="border-b border-slate-100 bg-slate-50/50 px-5 py-2 text-[8px] font-semibold uppercase tracking-[0.13em] text-slate-400"
                    >
                      {group}
                    </td>
                  </tr>
                  {rows
                    .filter((row) => row.group === group)
                    .map((row) => {
                      const outcomes = selected.map((competitor) =>
                        judge(row, row.mine, row.get(competitor)),
                      );
                      const mineLeads = outcomes.includes("mine");

                      return (
                        <tr
                          key={row.id}
                          className="group border-b border-slate-100 last:border-b-0 hover:bg-slate-50/30"
                        >
                          <td className="sticky left-0 z-10 bg-white px-5 py-3 group-hover:bg-slate-50/90">
                            <p className="text-[10.5px] font-medium text-slate-700">
                              {row.label}
                            </p>
                            <p className="mt-0.5 text-[8px] text-slate-400">{row.helper}</p>
                          </td>
                          <td
                            className={cn(
                              "border-l border-indigo-100/70 bg-indigo-50/20 px-4 py-3",
                              mineLeads && "bg-emerald-50/50",
                            )}
                          >
                            <div className="flex items-center gap-2">
                              <ValueCell value={row.mine} outcome="mine" emphasis />
                              {mineLeads ? (
                                <span className="rounded bg-emerald-100/80 px-1 py-0.5 text-[6.5px] font-semibold uppercase tracking-wide text-emerald-700">
                                  Lead
                                </span>
                              ) : null}
                            </div>
                          </td>
                          {selected.map((competitor, index) => {
                            const outcome = outcomes[index];
                            return (
                              <td
                                key={competitor.id}
                                className={cn(
                                  "border-l border-slate-100 px-4 py-3",
                                  outcome === "other" && "bg-amber-50/40",
                                )}
                              >
                                <ValueCell
                                  value={row.get(competitor)}
                                  outcome={outcome}
                                />
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {selected.length === 0 ? (
          <div className="border-t border-slate-100 bg-slate-50/50 px-5 py-3 text-center text-[9px] text-slate-400">
            Select at least one competitor to see differential highlighting.
          </div>
        ) : null}
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_312px]">
        <section className="print-avoid-break overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card">
          <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div>
              <h2 className="text-[15px] font-semibold tracking-tight text-ink">
                Price positioning
              </h2>
              <p className="mt-1 text-[10.5px] text-slate-500">
                Starting and Pro tiers across the selected set.
              </p>
            </div>
            <div className="flex items-center gap-4 text-[9px] text-slate-400">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-sm bg-indigo-200" />
                Starting
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-sm bg-indigo-600" />
                Pro
              </span>
            </div>
          </div>
          <div className="h-[310px] w-full px-2 pb-4 pt-6 sm:px-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barGap={5} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="startingFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#C7D2FE" />
                    <stop offset="100%" stopColor="#A5B4FC" />
                  </linearGradient>
                  <linearGradient id="proFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366F1" />
                    <stop offset="100%" stopColor="#4F46E5" />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#EEF2F7" />
                <XAxis
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 9, fill: "#94A3B8" }}
                  dy={8}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 9, fill: "#94A3B8" }}
                  tickFormatter={(value) => `$${value}`}
                  width={48}
                />
                <Tooltip
                  cursor={{ fill: "#F8FAFC" }}
                  contentStyle={{
                    borderRadius: 10,
                    border: "1px solid #E2E8F0",
                    boxShadow: "0 12px 30px -15px rgba(15,23,42,0.25)",
                    fontSize: 10,
                    padding: "8px 10px",
                  }}
                  formatter={(value, name) => [
                    formatCurrency(Number(value)),
                    name === "starting" ? "Starting tier" : "Pro tier",
                  ]}
                  labelStyle={{ fontSize: 10, fontWeight: 600, color: "#0F172A" }}
                />
                <Bar
                  dataKey="starting"
                  fill="url(#startingFill)"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={30}
                />
                <Bar
                  dataKey="pro"
                  fill="url(#proFill)"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={30}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="print-avoid-break relative overflow-hidden rounded-2xl bg-[#0B1120] p-5 text-white shadow-[0_24px_60px_-30px_rgba(15,23,42,0.6)]">
          <div className="pointer-events-none absolute -right-20 -top-20 h-52 w-52 rounded-full bg-cyan-500/15 blur-3xl" />
          <div className="relative">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.05] px-2 py-1 text-[8px] font-semibold uppercase tracking-[0.13em] text-cyan-300">
              <Sparkles className="h-2.5 w-2.5" />
              Market read
            </span>
            <h2 className="mt-3 text-[16px] font-semibold tracking-tight text-white">
              Price is not the whole story.
            </h2>
            <p className="mt-2 text-[10.5px] leading-relaxed text-slate-400">
              {lowestEntry.name === "Nexus Intel"
                ? "Nexus holds the lowest entry point in this comparison. Protect the gap with governance and coverage."
                : `${lowestEntry.name} enters at ${formatCurrency(lowestEntry.starting)}, below the selected set. Differentiate on depth, not discounts.`}{" "}
              The top Pro tier reaches {formatCurrency(highestPro.pro)}, a{" "}
              {formatCurrency(proSpread)} spread from the lowest starting plan.
            </p>

            <div className="mt-5 space-y-3 border-t border-white/[0.08] pt-4">
              <div className="flex gap-2.5">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/[0.06] text-indigo-300">
                  <Clock3 className="h-3 w-3" />
                </span>
                <div>
                  <p className="text-[10px] font-medium text-slate-200">Refresh advantage</p>
                  <p className="mt-0.5 text-[9px] leading-relaxed text-slate-500">
                    15-minute cadence is faster than every selected competitor.
                  </p>
                </div>
              </div>
              <div className="flex gap-2.5">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/[0.06] text-emerald-300">
                  <ShieldCheck className="h-3 w-3" />
                </span>
                <div>
                  <p className="text-[10px] font-medium text-slate-200">Governance is included</p>
                  <p className="mt-0.5 text-[9px] leading-relaxed text-slate-500">
                    SSO, SOC 2, and audit logs ship without an enterprise upgrade.
                  </p>
                </div>
              </div>
              <div className="flex gap-2.5">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/[0.06] text-amber-300">
                  <ArrowDownUp className="h-3 w-3" />
                </span>
                <div>
                  <p className="text-[10px] font-medium text-slate-200">Where to lead</p>
                  <p className="mt-0.5 text-[9px] leading-relaxed text-slate-500">
                    Anchor on auditability and unlimited signal coverage in mid-market deals.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
