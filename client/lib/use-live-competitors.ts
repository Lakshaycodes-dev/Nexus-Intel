"use client";

import { useEffect, useState } from "react";

import { getCompetitor, listCompetitors } from "./api";
import { competitorFromResponse } from "./adapters";
import type { Competitor } from "./types";

interface LiveCompetitorsState {
  competitors: Competitor[];
  loading: boolean;
  liveCount: number;
}

/**
 * Hydrates the static watchlist with the latest persisted analysis for each
 * competitor domain.
 *
 * It first asks `GET /api/v1/competitors` which domains have stored runs in the
 * signed-in workspace, then fetches only those briefs. Domains without a run
 * (or a signed-out/offline backend) transparently keep the fixture data.
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
      let tracked: Set<string>;
      try {
        const list = await listCompetitors(controller.signal);
        tracked = new Set(
          list.competitors
            .filter((entry) => entry.has_data)
            .map((entry) => entry.domain),
        );
      } catch {
        // Not signed in yet, or the backend is offline: keep the fixtures.
        if (!cancelled) {
          setState({ competitors: base, loading: false, liveCount: 0 });
        }
        return;
      }

      const results = await Promise.all(
        base.map(async (fallback) => {
          if (!tracked.has(fallback.domain)) {
            return { competitor: fallback, live: false };
          }
          try {
            const response = await getCompetitor(fallback.domain, controller.signal);
            return {
              competitor: competitorFromResponse(response, fallback) ?? fallback,
              live: true,
            };
          } catch {
            return { competitor: fallback, live: false };
          }
        }),
      );

      if (cancelled) return;

      setState({
        competitors: results.map((result) => result.competitor),
        loading: false,
        liveCount: results.filter((result) => result.live).length,
      });
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
