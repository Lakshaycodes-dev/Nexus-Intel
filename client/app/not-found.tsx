import Link from "next/link";
import { ArrowLeft, Compass, Radar } from "lucide-react";
import { Logo } from "@/components/logo";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#F8FAFC] px-5">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-[-200px] h-[420px] w-[680px] -translate-x-1/2 rounded-full bg-indigo-200/35 blur-[120px]" />
        <div className="absolute bottom-[-160px] right-[10%] h-72 w-72 rounded-full bg-cyan-200/30 blur-[100px]" />
        <div className="absolute inset-0 bg-dot-grid opacity-[0.2] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
      </div>

      <div className="relative w-full max-w-md rounded-2xl border border-slate-200/80 bg-white p-8 text-center shadow-float">
        <div className="flex justify-center">
          <Logo />
        </div>
        <span className="mt-7 inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-500">
          <Radar className="h-2.5 w-2.5 text-indigo-500" />
          Signal 404 · no match
        </span>
        <h1 className="mt-4 text-[24px] font-semibold tracking-[-0.035em] text-ink">
          This signal is off the map.
        </h1>
        <p className="mx-auto mt-2 max-w-xs text-[12px] leading-relaxed text-slate-500">
          The page you are looking for has moved, been archived, or never existed in this
          workspace.
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Link href="/dashboard" className={cn(buttonVariants({ size: "md" }))}>
            <Compass className="h-3.5 w-3.5" />
            Back to console
          </Link>
          <Link
            href="/"
            className={cn(buttonVariants({ variant: "secondary", size: "md" }))}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Return home
          </Link>
        </div>
      </div>
    </div>
  );
}
