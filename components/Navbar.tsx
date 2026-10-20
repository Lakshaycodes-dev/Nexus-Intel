import { Cloud, Radar, Sparkles } from "lucide-react";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-ink-950/70 backdrop-blur-2xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-400 to-cyan-400 shadow-glow-sm">
              <Radar className="h-5 w-5 text-white" strokeWidth={2.2} />
            </div>
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border border-ink-950 bg-emerald-400" />
          </div>

          <div className="leading-tight">
            <div className="flex items-center gap-1.5">
              <span className="text-[15px] font-semibold tracking-tight text-white">
                Nexus
              </span>
              <span className="text-[15px] font-semibold tracking-tight text-indigo-300">
                Intel
              </span>
            </div>
            <p className="hidden text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500 sm:block">
              Market &amp; Competitor Intelligence
            </p>
          </div>
        </div>

        <div className="hidden items-center gap-3 lg:flex">
          <div className="rounded-full bg-gradient-to-r from-indigo-500/60 via-sky-400/50 to-cyan-400/50 p-px shadow-glow-sm">
            <div className="flex items-center gap-2 rounded-full bg-ink-900/95 px-3 py-1.5">
              <Sparkles className="h-3.5 w-3.5 text-indigo-300" />
              <span className="text-[11px] font-medium text-slate-300">
                KriticalHacks 2026
              </span>
              <span className="text-slate-600">|</span>
              <span className="bg-gradient-to-r from-indigo-300 to-cyan-300 bg-clip-text text-[11px] font-semibold text-transparent">
                TinyFish Powered
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/[0.07] px-3 py-1.5 sm:flex">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </span>
            <span className="text-[11px] font-medium text-emerald-300">
              Engine: Active
            </span>
            <span className="h-3 w-px bg-emerald-400/20" />
            <Cloud className="h-3 w-3 text-emerald-400/80" />
            <span className="text-[11px] text-emerald-200/70">Serverless</span>
          </div>

          <div className="flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/[0.07] px-2.5 py-1.5 sm:hidden">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="text-[10px] font-medium text-emerald-300">Active</span>
          </div>
        </div>
      </div>

      <div className="hairline h-px w-full opacity-60" />
    </header>
  );
}
