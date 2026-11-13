"use client";

import { useEffect, useState } from "react";

import { getCompetitor } from "./api";
import { competitorFromResponse } from "./adapters";
import type { Competitor } from "./types";

interface LiveCompetitorsState {
  competitors: Competitor[];
  loading: boolean;
  liveCount: number;
}

/**
 * Hydrates the static watchlist with the latest persisted analysis for each
 * competitor domain (`GET /api/v1/competitors/{domain}`). Domains without a
 * stored run (404) or an offline backend transparently keep the fixture data.
 */
export function useLiveCompetitors(base: Competitor[]): LiveCompetitorsState {
  const [state, setState] = useState<LiveCompetitorsState>({
    competitors: base,
    loading: true,
    liveCount: 0,
  });

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    async function load() {
      const results = await Promise.allSettled(
        base.map(async (fallback) => {
          const response = await getCompetitor(fallback.domain, controller.signal);
          return competitorFromResponse(response, fallback) ?? fallback;
        }),
      );

      if (cancelled) return;

      let liveCount = 0;
      const competitors = results.map((result, index) => {
        if (result.status === "fulfilled") {
          liveCount += 1;
          return result.value;
        }
        return base[index];
      });

      setState({ competitors, loading: false, liveCount });
    }

    load();

    return () => {
      cancelled = true;
      controller.abort();
    };
    // The fixture watchlist is a module-level constant on every caller.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return state;
}
