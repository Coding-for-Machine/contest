"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Server,
  X,
  Loader2,
} from "lucide-react";
import type { TestcasePayload, FinalPayload } from "@/lib/sse/types";
import { formatMemory, formatTime } from "@/lib/problems/utils";
import { cn } from "@/lib/utils";

export type SubmissionStreamStatus = "queued" | "running" | "done" | "error";

export interface ActiveSubmission {
  id: string | number | null;
  testcases: TestcasePayload[];
  final: FinalPayload | null;
  errorMessage: string | null;
  status: SubmissionStreamStatus;
}

interface SubmissionTrackerProps {
  submission: ActiveSubmission | null;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
}

const STATUS_CONFIG: Record<
  string,
  { icon: React.ReactNode; label: string; color: string }
> = {
  AC: { icon: <CheckCircle2 className="size-4" />, label: "Accepted", color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  WA: { icon: <XCircle className="size-4" />, label: "Wrong Answer", color: "text-red-600 bg-red-50 border-red-200" },
  TLE: { icon: <Clock className="size-4" />, label: "Time Limit", color: "text-amber-600 bg-amber-50 border-amber-200" },
  MLE: { icon: <AlertTriangle className="size-4" />, label: "Memory Limit", color: "text-purple-600 bg-purple-50 border-purple-200" },
  RE: { icon: <AlertTriangle className="size-4" />, label: "Runtime Error", color: "text-orange-600 bg-orange-50 border-orange-200" },
  "Server Error": { icon: <Server className="size-4" />, label: "Server Error", color: "text-neutral-600 bg-neutral-50 border-neutral-200" },
};

function verdictInfo(verdict: string) {
  const normalized = verdict.toUpperCase();
  const isAccepted = normalized === "AC" || normalized === "ACCEPTED";
  return isAccepted
    ? { label: "Accepted", classes: "bg-emerald-50 border-emerald-200 text-emerald-700", icon: <CheckCircle2 className="size-7" /> }
    : { label: verdict, classes: "bg-red-50 border-red-200 text-red-700", icon: <XCircle className="size-7" /> };
}

export function SubmissionTracker({
  submission,
  open,
  onOpen,
  onClose,
}: SubmissionTrackerProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted || !submission) return null;

  const { testcases, final, errorMessage, status } = submission;
  const isRunning = status === "queued" || status === "running";
  const isFailed =
    status === "error" ||
    (final && final.passed_count !== final.total_count);

  if (!open) {
    return createPortal(
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          "fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-medium shadow-lg transition-colors",
          isRunning && "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100",
          !isRunning && !isFailed && "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
          !isRunning && isFailed && "border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
        )}
      >
        {isRunning ? (
          <Loader2 className="size-4 animate-spin" />
        ) : isFailed ? (
          <XCircle className="size-4" />
        ) : (
          <CheckCircle2 className="size-4" />
        )}
        {isRunning
          ? `Tekshirilmoqda... (${testcases.length})`
          : final
          ? verdictInfo(final.verdict).label
          : "Xatolik"}
      </button>,
      document.body
    );
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Yopish"
        onClick={onClose}
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
      />

      <div className="relative flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-neutral-900">
            Taqdimot natijasi
          </h2>
          <button
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            aria-label="Yopish"
          >
            <X className="size-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {status === "error" && (
            <div className="mb-5 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
              <AlertTriangle className="size-6 shrink-0" />
              <div>
                <p className="font-semibold">Xatolik yuz berdi</p>
                <p className="text-sm text-red-600">
                  {errorMessage ?? "Noma'lum xatolik"}
                </p>
              </div>
            </div>
          )}

          {isRunning && (
            <div className="mb-5 flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-700">
              <Loader2 className="size-6 shrink-0 animate-spin" />
              <div>
                <p className="font-semibold">
                  {status === "queued" ? "Navbatga qo'yildi..." : "Testlar tekshirilmoqda..."}
                </p>
                <p className="text-sm text-blue-600">
                  {testcases.length} ta test tekshirildi
                </p>
              </div>
            </div>
          )}

          {final && (
            <div
              className={cn(
                "mb-5 flex flex-col gap-4 rounded-xl border p-5 sm:flex-row sm:items-center",
                verdictInfo(final.verdict).classes
              )}
            >
              <div className="flex items-center gap-4">
                {verdictInfo(final.verdict).icon}
                <div>
                  <p className="text-xl font-bold">{verdictInfo(final.verdict).label}</p>
                  <p className="text-sm opacity-80">
                    {final.passed_count}/{final.total_count} ta test o'tdi
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 text-sm sm:ml-auto sm:text-right">
                <div>
                  <p className="opacity-60">Til</p>
                  <p className="font-semibold">{final.lang}</p>
                </div>
                <div>
                  <p className="opacity-60">Vaqt</p>
                  <p className="font-semibold">{formatTime(final.time)}</p>
                </div>
                <div>
                  <p className="opacity-60">Xotira</p>
                  <p className="font-semibold">{formatMemory(final.memory)}</p>
                </div>
              </div>
            </div>
          )}

          {final && final.total_count > 0 && (
            <div className="mb-5">
              <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    final.passed_count === final.total_count ? "bg-emerald-500" : "bg-red-400"
                  )}
                  style={{ width: `${(final.passed_count / final.total_count) * 100}%` }}
                />
              </div>
            </div>
          )}

          {isRunning && testcases.length > 0 && (
            <div className="mb-5 flex flex-wrap gap-1.5">
              {testcases
                .slice()
                .sort((a, b) => a.index - b.index)
                .map((tc) => {
                  const ok = tc.status === "AC";
                  return (
                    <span
                      key={tc.index}
                      title={`Test #${tc.index}: ${tc.status}`}
                      className={cn(
                        "flex size-7 items-center justify-center rounded-md text-[11px] font-semibold",
                        ok ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                      )}
                    >
                      {tc.index}
                    </span>
                  );
                })}
            </div>
          )}

          {testcases.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-neutral-700">Testlar tafsiloti</h3>
              {testcases
                .slice()
                .sort((a, b) => a.index - b.index)
                .map((tc) => {
                  const config = STATUS_CONFIG[tc.status] || STATUS_CONFIG["Server Error"];
                  return (
                    <div key={tc.index} className={cn("rounded-lg border p-3", config.color)}>
                      <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {config.icon}
                          <span className="text-xs font-semibold">
                            Test #{tc.index} — {config.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs opacity-80">
                          {tc.cpu_time != null && <span>{tc.cpu_time} ms</span>}
                          {tc.memory != null && <span>{formatMemory(tc.memory)}</span>}
                        </div>
                      </div>

                      {tc.status !== "AC" && (
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                          <MiniField label="Input" value={tc.input} />
                          <MiniField label="Kutilgan" value={tc.expected_output} />
                          <MiniField label="Sizning javob" value={tc.output || "(bo'sh)"} />
                        </div>
                      )}

                      {tc.message && (
                        <pre className="mt-2 overflow-x-auto rounded bg-white/60 p-2 font-mono text-[11px] text-red-600">
                          {tc.message}
                        </pre>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

function MiniField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-[10px] font-medium uppercase opacity-70">{label}</span>
      <pre className="mt-0.5 overflow-x-auto rounded bg-white/50 p-2 font-mono text-[11px]">
        {value}
      </pre>
    </div>
  );
}