import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { FlickCards } from "@/components/marketing/flick-cards";

export function Capabilities() {
  return (
    <section id="capabilities" className="relative py-20 sm:py-28">
      <div className="page-shell">
        <div className="grid gap-6 lg:grid-cols-[1fr_0.8fr] lg:items-end">
          <div>
            <p className="eyebrow">Capabilities</p>
            <h2 className="mt-4 max-w-[620px] text-balance text-3xl font-semibold leading-[1.12] tracking-[-0.035em] text-ink sm:text-[42px]">
              Six layers of unfair advantage.
            </h2>
          </div>
          <div className="lg:pb-1">
            <p className="max-w-md text-[14px] leading-relaxed text-slate-500">
              Most tools watch a page. Nexus understands the market around it — what changed,
              what it means, and what to do next.
            </p>
            <Link
              href="#product"
              className="mt-4 inline-flex items-center gap-1.5 text-[12px] font-semibold text-indigo-600 transition hover:text-indigo-800"
            >
              See the intelligence engine
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        <div className="mt-10">
          <FlickCards />
        </div>
      </div>
    </section>
  );
}
