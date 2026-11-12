"use client";

import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

export function ApiStatus({ className }: { className?: string }) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let active = true;
    getHealth()
      .then((response) => {
        if (active) setHealth(response);
      })
      .catch(() => {
        if (active) setOffline(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const connected = health?.database === "connected";
  const label = offline
    ? "API offline"
    : health
      ? connected
        ? "API online"
        : "API degraded"
      : "Checking API";

  return (
    <span
      title={
        health
          ? `Nexus-Intel ${health.version} · mock mode ${health.mock_mode ? "on" : "off"} · database ${health.database}`
          : "GET /health"
      }
      className={cn(
        "inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-[10px] font-medium text-slate-500 shadow-sm",
        className,
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          offline
            ? "bg-rose-500"
            : connected
              ? "animate-pulse-soft bg-emerald-500"
              : health
                ? "bg-amber-500"
                : "bg-slate-300",
        )}
      />
      {label}
    </span>
  );
}
