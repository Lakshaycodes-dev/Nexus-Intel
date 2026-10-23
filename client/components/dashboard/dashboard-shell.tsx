"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  Boxes,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Command,
  Compass,
  LayoutDashboard,
  Menu,
  Plus,
  Radar,
  Search,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { Logo, NexusMark } from "@/components/logo";
import { cn } from "@/lib/utils";

const primaryNav = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard, badge: null },
  { label: "Competitors", href: "/dashboard#competitors", icon: Compass, badge: null },
  { label: "Live Signals", href: "/dashboard#signals", icon: Radar, badge: "6" },
  { label: "Comparison", href: "/dashboard/compare", icon: Boxes, badge: null },
];

const secondaryNav = [
  { label: "Settings", href: "/dashboard", icon: Settings },
  { label: "Help & docs", href: "/dashboard", icon: CircleHelp },
];

function SidebarContent({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-[68px] shrink-0 items-center justify-between px-5">
        <Logo href="/dashboard" />
        {onNavigate ? (
          <button
            type="button"
            onClick={onNavigate}
            aria-label="Close navigation"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 text-slate-500"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4">
        <button
          type="button"
          className="mt-1 flex w-full items-center gap-2.5 rounded-xl border border-slate-200/80 bg-slate-50/60 px-2.5 py-2 text-left transition hover:border-slate-300 hover:bg-slate-50"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 text-[10px] font-semibold text-white">
            A
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[11px] font-semibold text-slate-800">
              Acme Corp
            </span>
            <span className="block truncate text-[9px] text-slate-400">Growth workspace</span>
          </span>
          <ChevronDown className="h-3 w-3 text-slate-400" />
        </button>

        <div className="mt-6">
          <p className="px-2.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Workspace
          </p>
          <nav className="mt-2 space-y-0.5">
            {primaryNav.map((item) => {
              const Icon = item.icon;
              const active =
                item.href === "/dashboard"
                  ? pathname === "/dashboard"
                  : item.href === "/dashboard#competitors"
                    ? pathname.includes("/competitors")
                    : item.href === "/dashboard#signals"
                      ? false
                      : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={onNavigate}
                  className={cn(
                    "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] font-medium transition-colors",
                    active
                      ? "bg-indigo-50/80 text-indigo-700"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-800",
                  )}
                >
                  {active ? (
                    <span className="absolute -left-3 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-indigo-500" />
                  ) : null}
                  <Icon
                    className={cn(
                      "h-[15px] w-[15px]",
                      active ? "text-indigo-600" : "text-slate-400 group-hover:text-slate-500",
                    )}
                  />
                  <span className="flex-1">{item.label}</span>
                  {item.badge ? (
                    <span
                      className={cn(
                        "flex h-[17px] min-w-[17px] items-center justify-center rounded-full px-1 text-[8px] font-semibold",
                        active ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-500",
                      )}
                    >
                      {item.badge}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-6">
          <p className="px-2.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            Manage
          </p>
          <nav className="mt-2 space-y-0.5">
            {secondaryNav.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={onNavigate}
                  className="group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] font-medium text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-800"
                >
                  <Icon className="h-[15px] w-[15px] text-slate-400 group-hover:text-slate-500" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-7 overflow-hidden rounded-xl border border-indigo-100/80 bg-gradient-to-b from-indigo-50/80 via-white to-white p-3.5">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[0.13em] text-indigo-600">
              <Sparkles className="h-3 w-3" />
              Coverage
            </span>
            <span className="font-mono text-[9px] text-slate-400">78%</span>
          </div>
          <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
            12 new sources connected across your market.
          </p>
          <div className="mt-2.5 h-1 overflow-hidden rounded-full bg-indigo-100">
            <div className="h-full w-[78%] rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" />
          </div>
          <Link
            href="/dashboard#competitors"
            onClick={onNavigate}
            className="mt-3 flex items-center justify-between rounded-md bg-white px-2 py-1.5 text-[9px] font-medium text-slate-600 shadow-sm ring-1 ring-slate-200/70 transition hover:text-indigo-600"
          >
            Expand coverage
            <ChevronRight className="h-2.5 w-2.5" />
          </Link>
        </div>
      </div>

      <div className="border-t border-slate-200/70 p-3">
        <div className="flex items-center gap-2.5 rounded-xl px-2 py-1.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-cyan-400 text-[10px] font-semibold text-white shadow-sm">
            AL
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-semibold text-slate-800">Alex Laurent</p>
            <p className="truncate text-[9px] text-slate-400">Command plan</p>
          </div>
          <Link
            href="/dashboard"
            aria-label="Account settings"
            className="flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <Settings className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!mobileOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMobileOpen(false);
    }
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [mobileOpen]);

  return (
    <div className="min-h-screen bg-[#F6F7FB]">
      <aside
        data-print-hide
        className="fixed inset-y-0 left-0 z-40 hidden w-[260px] border-r border-slate-200/80 bg-white/90 backdrop-blur-xl lg:block"
      >
        <SidebarContent pathname={pathname} />
      </aside>

      <AnimatePresence>
        {mobileOpen ? (
          <div className="fixed inset-0 z-[60] lg:hidden">
            <motion.button
              type="button"
              aria-label="Close navigation overlay"
              className="absolute inset-0 h-full w-full cursor-default bg-slate-950/25 backdrop-blur-[2px]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 30, stiffness: 320 }}
              className="relative h-full w-[268px] border-r border-slate-200 bg-white shadow-2xl"
            >
              <SidebarContent pathname={pathname} onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </div>
        ) : null}
      </AnimatePresence>

      <div className="lg:pl-[260px] print:pl-0">
        <header
          data-print-hide
          className="sticky top-0 z-30 flex h-[64px] items-center gap-3 border-b border-slate-200/70 bg-white/80 px-4 backdrop-blur-xl sm:px-6"
        >
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>

          <div className="flex items-center gap-2 lg:hidden">
            <NexusMark />
          </div>

          <div className="hidden items-center gap-1.5 text-[11px] text-slate-400 md:flex">
            <span>Workspace</span>
            <ChevronRight className="h-3 w-3" />
            <span className="font-medium text-slate-600">
              {pathname === "/dashboard"
                ? "Overview"
                : pathname.includes("compare")
                  ? "Comparison"
                  : "Intelligence brief"}
            </span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <div className="hidden h-9 w-[230px] items-center gap-2 rounded-lg border border-slate-200/80 bg-slate-50/70 px-3 text-slate-400 transition focus-within:border-indigo-200 focus-within:bg-white focus-within:ring-2 focus-within:ring-indigo-500/10 md:flex xl:w-[280px]">
              <Search className="h-3.5 w-3.5" />
              <input
                placeholder="Search competitors, signals..."
                aria-label="Search"
                className="h-full min-w-0 flex-1 border-0 bg-transparent p-0 text-[11px] text-slate-600 placeholder:text-slate-400 focus:ring-0"
              />
              <span className="flex items-center gap-0.5 rounded border border-slate-200 bg-white px-1 py-0.5 font-mono text-[8px] text-slate-400">
                <Command className="h-2 w-2" />K
              </span>
            </div>

            <Link
              href="/dashboard#scan"
              className="hidden h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-[11px] font-medium text-slate-600 shadow-sm transition hover:border-slate-300 hover:text-slate-900 sm:flex"
            >
              <Plus className="h-3.5 w-3.5" />
              New scan
            </Link>

            <button
              type="button"
              aria-label="Notifications"
              className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:text-slate-900"
            >
              <Bell className="h-3.5 w-3.5" />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-rose-500 ring-2 ring-white" />
            </button>

            <div className="ml-0.5 flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-cyan-400 text-[10px] font-semibold text-white shadow-sm ring-2 ring-white">
              AL
            </div>
          </div>
        </header>

        <main className="min-h-[calc(100vh-64px)]">{children}</main>
      </div>
    </div>
  );
}
