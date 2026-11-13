/**
 * Small browser-side store of recent analysis IDs so the dashboard can re-read
 * completed runs through `GET /api/v1/analyze/{id}`.
 */

export const RECENT_ANALYSES_KEY = "nexus-intel:recent-analyses";
export const ANALYSIS_COMPLETE_EVENT = "nexus-intel:analysis-complete";

export interface RecentAnalysisEntry {
  analysis_id: string;
  domain: string;
  created_at: string;
}

function isEntry(value: unknown): value is RecentAnalysisEntry {
  if (!value || typeof value !== "object") return false;
  const entry = value as Partial<RecentAnalysisEntry>;
  return (
    typeof entry.analysis_id === "string" &&
    typeof entry.domain === "string" &&
    typeof entry.created_at === "string"
  );
}

export function readRecentAnalyses(): RecentAnalysisEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_ANALYSES_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isEntry).slice(0, 5);
  } catch {
    return [];
  }
}

export function rememberAnalysis(entry: RecentAnalysisEntry): void {
  if (typeof window === "undefined") return;
  const next = [
    entry,
    ...readRecentAnalyses().filter(
      (item) => item.analysis_id !== entry.analysis_id,
    ),
  ].slice(0, 5);

  try {
    window.localStorage.setItem(RECENT_ANALYSES_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent(ANALYSIS_COMPLETE_EVENT));
  } catch {
    // Storage can be disabled (private mode); the scan still succeeds.
  }
}
