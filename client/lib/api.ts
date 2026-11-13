/**
 * Typed client for the Nexus-Intel FastAPI backend.
 *
 * Endpoints (mounted under `/api/v1`):
 *   POST /api/v1/analyze              -> run a competitor analysis
 *   GET  /api/v1/analyze/{id}         -> read an analysis record
 *   GET  /api/v1/competitors/{id}     -> read the latest competitor brief
 *   GET  /health                      -> API + database health
 *
 * The base URL comes from `NEXT_PUBLIC_API_URL` (see `client/.env.example`) and
 * defaults to the local FastAPI server used by `uvicorn app.main:app`.
 */

import type { ScopeKey } from "./types";

const DEFAULT_API_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  return (configured || DEFAULT_API_URL).replace(/\/+$/, "");
}

// --- Response contracts (mirror app/schemas.py) ---------------------------- //

export type AnalysisStatus = "queued" | "running" | "completed" | "failed";

export type ApiSentiment = "positive" | "threat" | "neutral";

export interface AnalysisParameters {
  pricing_tiers: boolean;
  feature_accordions: boolean;
  offsite_mentions: boolean;
}

export interface PricingEntry {
  tier: string;
  monthly: string;
  annual: string;
  features: string[];
}

export interface NewsEntry {
  title: string;
  source: string;
  url: string | null;
  sentiment: ApiSentiment;
}

export interface CapabilityEntry {
  name: string;
  traditionalScraper: boolean;
  nexusIntel: boolean;
}

export interface CompetitorData {
  domain: string;
  pricing: PricingEntry[];
  offsiteNews: NewsEntry[];
  capabilities: CapabilityEntry[];
  executionTimeSec: number;
}

export interface ExtractionSummary {
  target: string;
  provenance: string | null;
  missing_fields: string[];
  warnings: string[];
  error: string | null;
}

export interface AnalyzeRequest {
  domain: string;
  parameters?: Partial<AnalysisParameters>;
  query?: string;
  mock?: boolean;
}

export interface AnalyzeResponse {
  analysis_id: string;
  status: AnalysisStatus;
  domain: string;
  query: string;
  mock: boolean;
  created_at: string;
  completed_at: string | null;
  execution_time_sec: number;
  report_path: string | null;
  extractions: ExtractionSummary[];
  data: CompetitorData;
}

export interface AnalysisRecord {
  analysis_id: string;
  domain: string;
  query: string;
  mock: boolean;
  status: AnalysisStatus;
  parameters: AnalysisParameters;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  execution_time_sec: number | null;
  report_path: string | null;
  extractions: ExtractionSummary[];
  data: CompetitorData | null;
  error: { code?: string; message?: string } | null;
}

export interface CompetitorResponse {
  competitor_id: string;
  domain: string;
  analysis_id: string;
  status: AnalysisStatus;
  created_at: string;
  updated_at: string;
  data: CompetitorData | null;
  error: { code?: string; message?: string } | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  service: string;
  version: string;
  mock_mode: boolean;
  database: "connected" | "unavailable";
  timestamp: string;
}

interface ApiValidationDetail {
  loc: string[];
  message: string;
  type: string;
}

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: ApiValidationDetail[];
  };
}

// --- Errors ---------------------------------------------------------------- //

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: ApiValidationDetail[];

  constructor(
    message: string,
    options: { code?: string; status?: number; details?: ApiValidationDetail[] } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.code = options.code ?? "api_error";
    this.status = options.status ?? 0;
    this.details = options.details ?? [];
  }

  static fromResponse(status: number, body: unknown): ApiError {
    const envelope = (body ?? {}) as ApiErrorEnvelope;
    const detail = envelope.error;
    return new ApiError(
      detail?.message || defaultMessageForStatus(status),
      {
        code: detail?.code ?? `http_${status}`,
        status,
        details: detail?.details,
      },
    );
  }
}

function defaultMessageForStatus(status: number): string {
  if (status === 404) return "No analysis was found for that competitor yet.";
  if (status === 422) return "The request could not be validated.";
  if (status === 502) return "The analysis pipeline could not complete the scan.";
  if (status === 503) return "The backend database is unavailable right now.";
  if (status === 504) return "The analysis timed out before completing.";
  if (status >= 500) return "The Nexus-Intel API hit an unexpected error.";
  return "The request to the Nexus-Intel API failed.";
}

// --- Low-level request helper ---------------------------------------------- //

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 15_000;
const ANALYZE_TIMEOUT_MS = 310_000;

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal, headers, ...init } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const requestHeaders = new Headers(headers);
    requestHeaders.set("Accept", "application/json");
    if (init.body) requestHeaders.set("Content-Type", "application/json");

    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
      cache: init.cache ?? "no-store",
      headers: requestHeaders,
      signal: controller.signal,
    });

    const text = await response.text();
    let body: unknown = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = { error: { code: "invalid_response", message: text } };
      }
    }

    if (!response.ok) throw ApiError.fromResponse(response.status, body);
    return body as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The request to the Nexus-Intel API timed out.", {
        code: "request_timeout",
      });
    }
    throw new ApiError(
      "Could not reach the Nexus-Intel API. Make sure the backend is running.",
      { code: "network_error" },
    );
  } finally {
    clearTimeout(timer);
  }
}

// --- Public endpoint wrappers ---------------------------------------------- //

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { timeoutMs: 5_000, signal });
}

export function analyzeCompetitor(
  input: AnalyzeRequest,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/v1/analyze", {
    method: "POST",
    body: JSON.stringify({
      domain: input.domain,
      ...(input.parameters ? { parameters: input.parameters } : {}),
      ...(input.query ? { query: input.query } : {}),
      ...(input.mock === undefined ? {} : { mock: input.mock }),
    }),
    timeoutMs: ANALYZE_TIMEOUT_MS,
    signal,
  });
}

export function getAnalysis(
  analysisId: string,
  signal?: AbortSignal,
): Promise<AnalysisRecord> {
  return request<AnalysisRecord>(
    `/api/v1/analyze/${encodeURIComponent(analysisId)}`,
    { signal },
  );
}

export function getCompetitor(
  competitorIdOrDomain: string,
  signal?: AbortSignal,
): Promise<CompetitorResponse> {
  return request<CompetitorResponse>(
    `/api/v1/competitors/${encodeURIComponent(competitorIdOrDomain)}`,
    { signal },
  );
}

// --- Helpers --------------------------------------------------------------- //

/** Mirror of the backend/frontend normalisation rule. */
export function normalizeDomain(input: string): string | null {
  const value = input
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/^www\./i, "")
    .split("/")[0]
    .split(":")[0]
    .toLowerCase();

  if (
    !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$/.test(
      value,
    )
  ) {
    return null;
  }
  return value;
}

/** Map the scanner's scope toggles onto the backend's analysis parameters. */
export function scopesToParameters(scopes: ScopeKey[]): AnalysisParameters {
  const selected = new Set(scopes);
  return {
    pricing_tiers: selected.has("pricing"),
    feature_accordions: selected.has("product"),
    offsite_mentions: selected.has("news"),
  };
}

export function isCompetitorData(value: unknown): value is CompetitorData {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<CompetitorData>;
  return (
    typeof candidate.domain === "string" &&
    Array.isArray(candidate.pricing) &&
    Array.isArray(candidate.offsiteNews) &&
    Array.isArray(candidate.capabilities) &&
    typeof candidate.executionTimeSec === "number"
  );
}
