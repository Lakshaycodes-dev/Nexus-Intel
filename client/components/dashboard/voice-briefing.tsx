"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AudioLines,
  Clock3,
  Headphones,
  Loader2,
  Newspaper,
  Sparkles,
  TrendingUp,
  Volume2,
} from "lucide-react";

import {
  ApiError,
  getBriefingAudio,
  getBriefingSummary,
  type BriefingChange,
  type BriefingSummary,
  type BriefingWindow,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const windows: Array<{ key: BriefingWindow; label: string }> = [
  { key: "24h", label: "Last 24 hours" },
  { key: "7d", label: "Last 7 days" },
];

function ChangeIcon({ type }: { type: BriefingChange["change_type"] }) {
  if (type === "pricing") return <TrendingUp className="h-3 w-3" />;
  if (type === "news") return <Newspaper className="h-3 w-3" />;
  if (type === "capability") return <Sparkles className="h-3 w-3" />;
  return <Clock3 className="h-3 w-3" />;
}

const sentimentStyle: Record<BriefingChange["sentiment"], string> = {
  positive: "border-emerald-100 bg-emerald-50 text-emerald-700",
  threat: "border-rose-100 bg-rose-50 text-rose-600",
  neutral: "border-slate-200 bg-slate-50 text-slate-500",
};

export function VoiceBriefing({ className }: { className?: string }) {
  const { user, loading: authLoading } = useAuth();
  const [range, setRange] = useState<BriefingWindow>("24h");
  const [summary, setSummary] = useState<BriefingSummary | null>(null);
  const [summaryFor, setSummaryFor] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [errorFor, setErrorFor] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);

  const activeSummary =
    user && summary && summaryFor === user.user_id ? summary : null;
  const activeError =
    user && summaryError && errorFor === user.user_id ? summaryError : null;
  // Derived, so the effect never has to synchronously flip a loading flag.
  const summaryLoading = Boolean(user) && !activeSummary && !activeError;

  useEffect(() => {
    if (!user) return;

    const controller = new AbortController();

    getBriefingSummary(range, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setSummary(data);
        setSummaryFor(user.user_id);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSummaryError(
          error instanceof ApiError
            ? error.message
            : "Could not load the market briefing.",
        );
        setErrorFor(user.user_id);
      });

    return () => controller.abort();
  }, [range, reloadToken, user]);

  function selectRange(next: BriefingWindow) {
    if (next === range || audioLoading) return;
    setRange(next);
    // A new window means a new digest and a new audio clip.
    setSummary(null);
    setSummaryFor(null);
    setSummaryError(null);
    setErrorFor(null);
    setAudioUrl(null);
    setAudioError(null);
  }

  // Object URLs must be revoked when replaced or unmounted.
  useEffect(() => {
    if (!audioUrl) return;
    return () => URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  async function generateAudio() {
    if (!user || audioLoading || summaryLoading || !activeSummary) return;
    setAudioLoading(true);
    setAudioError(null);
    try {
      const blob = await getBriefingAudio(range);
      setAudioUrl(URL.createObjectURL(blob));
    } catch (error) {
      setAudioUrl(null);
      setAudioError(
        error instanceof ApiError
          ? error.message
          : "Could not generate the voice briefing.",
      );
    } finally {
      setAudioLoading(false);
    }
  }

  const visibleChanges = useMemo(
    () => activeSummary?.changes.slice(0, 8) ?? [],
    [activeSummary],
  );

  return (
    <section
      className={cn(
        "overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-card",
        className,
      )}
    >
      <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-indigo-100 bg-indigo-50 text-indigo-600">
            <AudioLines className="h-4 w-4" />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-[14px] font-semibold tracking-tight text-ink">
                AI voice briefing
              </h2>
              <span className="rounded-full border border-indigo-100 bg-indigo-50 px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.1em] text-indigo-600">
                ElevenLabs
              </span>
            </div>
            <p className="mt-1 text-[10px] text-slate-400">
              Spoken summary of competitor pricing and news changes from your stored
              analyses.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-full border border-slate-200 bg-slate-50 p-0.5">
            {windows.map((option) => (
              <button
                key={option.key}
                type="button"
                onClick={() => selectRange(option.key)}
                disabled={audioLoading}
                aria-pressed={range === option.key}
                className={cn(
                  "rounded-full px-2.5 py-1 text-[10px] font-semibold transition disabled:opacity-50",
                  range === option.key
                    ? "bg-white text-indigo-600 shadow-sm"
                    : "text-slate-500 hover:text-slate-700",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={generateAudio}
            disabled={!user || !activeSummary || audioLoading || summaryLoading}
            className={cn(
              buttonVariants({ variant: "primary", size: "xs" }),
              "gap-1.5 px-3",
            )}
          >
            {audioLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Headphones className="h-3 w-3" />
            )}
            {audioLoading ? "Synthesizing…" : "Play briefing"}
          </button>
        </div>
      </div>

      <div className="px-5 py-4">
        {authLoading ? (
          <p className="text-[10px] text-slate-400">Checking your workspace…</p>
        ) : !user ? (
          <div className="flex flex-col items-start gap-2 rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[11.5px] font-medium text-slate-700">
                Sign in to hear your market briefing
              </p>
              <p className="mt-0.5 text-[10px] text-slate-400">
                Briefings are generated from your workspace&apos;s stored analyses.
              </p>
            </div>
            <Link
              href={`/login?next=${encodeURIComponent("/dashboard")}`}
              className={cn(
                buttonVariants({ variant: "secondary", size: "xs" }),
                "px-3",
              )}
            >
              Sign in
            </Link>
          </div>
        ) : activeError ? (
          <div className="flex items-start gap-2 rounded-xl border border-rose-100 bg-rose-50 px-3 py-2.5 text-[10.5px] text-rose-600">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <div className="flex-1">
              {activeError}
              <button
                type="button"
                onClick={() => {
                  setSummaryError(null);
                  setErrorFor(null);
                  setReloadToken((token) => token + 1);
                }}
                className="ml-2 font-semibold underline underline-offset-2"
              >
                Retry
              </button>
            </div>
          </div>
        ) : !activeSummary ? (
          <div className="animate-pulse space-y-2">
            <div className="h-3 w-2/3 rounded bg-slate-100" />
            <div className="h-3 w-1/2 rounded bg-slate-100" />
            <div className="h-10 w-full rounded-xl bg-slate-100" />
          </div>
        ) : (
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 flex-1">
              <p className="text-[12.5px] font-medium text-slate-800">
                {activeSummary.headline}
              </p>
              <p className="mt-1 text-[10px] text-slate-400">
                {activeSummary.record_count}{" "}
                {activeSummary.record_count === 1 ? "recorded run" : "recorded runs"} ·{" "}
                {activeSummary.domains.length}{" "}
                {activeSummary.domains.length === 1 ? "competitor" : "competitors"} ·
                generated{" "}
                {new Date(activeSummary.generated_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>

              <div className="mt-3 max-h-56 space-y-1.5 overflow-y-auto pr-1">
                {visibleChanges.length > 0 ? (
                  visibleChanges.map((change, index) => (
                    <div
                      key={`${change.domain}-${change.change_type}-${index}`}
                      className="flex items-start gap-2 rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2"
                    >
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500">
                        <ChangeIcon type={change.change_type} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] font-semibold text-slate-700">
                            {change.title}
                          </span>
                          <span className="rounded-full bg-white px-1.5 py-0.5 font-mono text-[8px] text-slate-400">
                            {change.domain}
                          </span>
                          {change.sentiment !== "neutral" ? (
                            <span
                              className={cn(
                                "rounded-full border px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-[0.08em]",
                                sentimentStyle[change.sentiment],
                              )}
                            >
                              {change.sentiment}
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-0.5 text-[10px] leading-relaxed text-slate-500">
                          {change.detail}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-200 px-3 py-4 text-center text-[10px] text-slate-400">
                    No competitor changes recorded in this window.{" "}
                    <Link href="#scan" className="font-semibold text-indigo-600">
                      Run a scan
                    </Link>{" "}
                    to start tracking.
                  </div>
                )}
              </div>
            </div>

            <div className="w-full shrink-0 lg:w-[300px]">
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <span className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                  <Volume2 className="h-3 w-3" />
                  Briefing script
                </span>
                <p className="mt-1.5 max-h-28 overflow-y-auto text-[10.5px] leading-relaxed text-slate-600">
                  {activeSummary.script}
                </p>
                {audioUrl ? (
                  <audio
                    src={audioUrl}
                    controls
                    autoPlay
                    className="mt-2.5 w-full"
                  />
                ) : null}
                {audioError ? (
                  <p className="mt-2 flex items-start gap-1.5 text-[10px] leading-relaxed text-rose-600">
                    <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
                    {audioError}
                  </p>
                ) : null}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
