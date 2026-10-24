import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Logo } from "@/components/logo";

const columns = [
  {
    title: "Product",
    links: ["Market monitoring", "Pricing intelligence", "Executive briefs", "Comparison matrices"],
  },
  {
    title: "Solutions",
    links: ["Revenue teams", "Product marketing", "Strategy & ops", "Founder-led sales"],
  },
  {
    title: "Company",
    links: ["About", "Customers", "Security", "Careers"],
  },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200/80 bg-white">
      <div className="page-shell py-14">
        <div className="grid gap-12 lg:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div className="max-w-xs">
            <Logo />
            <p className="mt-4 text-[13px] leading-relaxed text-slate-500">
              Autonomous market and competitor intelligence for teams that refuse to be surprised.
            </p>
            <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] text-slate-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              All systems operational
            </div>
          </div>

          {columns.map((column) => (
            <div key={column.title}>
              <p className="eyebrow">{column.title}</p>
              <ul className="mt-4 space-y-2.5">
                {column.links.map((link) => (
                  <li key={link}>
                    <Link
                      href="#"
                      className="text-[13px] text-slate-500 transition-colors hover:text-slate-900"
                    >
                      {link}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-slate-100 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[11px] text-slate-400">
            © {new Date().getFullYear()} Nexus Intel, Inc. All rights reserved.
          </p>
          <div className="flex flex-wrap items-center gap-5">
            <Link href="#" className="text-[11px] text-slate-400 hover:text-slate-700">
              Privacy
            </Link>
            <Link href="#" className="text-[11px] text-slate-400 hover:text-slate-700">
              Terms
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 hover:text-indigo-600"
            >
              Enter console
              <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
