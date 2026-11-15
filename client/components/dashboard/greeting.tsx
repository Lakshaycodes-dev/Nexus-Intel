"use client";

import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

/**
 * Personalised dashboard heading.
 *
 * Falls back to the demo name until the session is restored so the server and
 * first client render stay identical (no hydration mismatch).
 */
export function Greeting({ className }: { className?: string }) {
  const { user } = useAuth();
  const firstName = user?.name?.trim().split(/\s+/)[0] || "Lakshay";

  return (
    <h1
      className={cn(
        "mt-3 text-[28px] font-semibold tracking-[-0.035em] text-ink sm:text-[32px]",
        className,
      )}
    >
      Good morning, {firstName}.
    </h1>
  );
}
