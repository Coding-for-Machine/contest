"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import useSWR from "swr";
import {
  X,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Server,
  Loader2,
  Copy,
  Check,
  Terminal,
  ChevronDown,
  ChevronUp,
  Bug,
} from "lucide-react";
import { getSubmissionDetail } from "@/lib/problems/api";
import type { SubmissionDetail, SubmissionTestResult } from "@/lib/problems/types";
import { formatMemory, formatTime, formatDateTime } from "@/lib/problems/utils";
import { cn } from "@/lib/utils";

interface SubmissionDetailModalProps {
  submissionId: number | null;
  open: boolean;
  onClose: () => void;
}

const VERDICT_CONFIG: Record<
  string,
  { icon: React.ReactNode; label: string; color: string; bg: string; border: string }
> = {
  AC: {
    icon: <CheckCircle2 className="size-5" />,
    label: "Accepted",
    color: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  WA: {
    icon: <XCircle className="size-5" />,
    label: "Wrong Answer",
    color: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-200",
  },
  TLE: {
    icon: <Clock className="size-5" />,
    label: "Time Limit",
    color: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  MLE: {
    icon: <AlertTriangle className="size-5" />,
    label: "Memory Limit",
    color: "text-purple-700",
    bg: "bg-purple-50",
    border: "border-purple-200",
  },
  RE: {
    icon: <AlertTriangle className="size-5" />,
    label: "Runtime Error",
    color: "text-orange-700",
    bg: "bg-orange-50",
    border: "border-orange-200",
  },
  CE: {
    icon: <Server className="size-5" />,
    label: "Compile Error",
    color: "text-neutral-700",
    bg: "bg-neutral-50",
    border: "border-neutral-200",
  },
};

function getVerdict(verdict: string) {
  return VERDICT_CONFIG[verdict?.toUpperCase()] || VERDICT_CONFIG["CE"];
}

export function SubmissionDetailModal({
  submissionId,
  open,
  onClose,
}: SubmissionDetailModalProps) {
  const [mounted, setMounted] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expandedTest, setExpandedTest] = useState<number | null>(null);

  useEffect(() => setMounted(true), []);

  const {
    data: submission,
    isLoading,
    error,
  } = useSWR<SubmissionDetail>(
    submissionId ? `submission-detail-${submissionId}` : null,
    () => getSubmissionDetail(submissionId!),
    { revalidateOnFocus: false }
  );

  useEffect(() => {
    if (!open) {
      setCopied(false);
      setExpandedTest(null);
    }
  }, [open]);

  if (!mounted || !open) return null;

  const handleCopyCode = async () => {
    if (!submission?.code) return;
    await navigator.clipboard.writeText(submission.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const toggleTest = (idx: number) => {
    setExpandedTest((prev) => (prev === idx ? null : idx));
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Yopish"
        onClick={onClose}
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
      />

      <div className="relative flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">
              Taqdimot #{submissionId}
            </h2>
            <p className="text-xs text-neutral-400">
              {submission?.problem?.title || "Yuklanmoqda..."}
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            aria-label="Yopish"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {isLoading && (
            <div className="flex h-48 flex-col items-center justify-center gap-3 text-neutral-400">
              <Loader2 className="size-6 animate-spin text-orange-500" />
              <p className="text-sm">Ma'lumotlar yuklanmoqda...</p>
            </div>
          )}

          {error && (
            <div className="flex h-48 flex-col items-center justify-center gap-2 text-center">
              <AlertTriangle className="size-10 text-red-300" />
              <p className="text-sm font-medium text-red-600">
                Ma'lumotlarni yuklashda xatolik
              </p>
              <p className="text-xs text-red-400">
                Qayta urinish tugmasini bosing
              </p>
            </div>
          )}

          {submission && (
            <div className="space-y-5">
              {/* Status Banner */}
              <div
                className={cn(
                  "flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center",
                  getVerdict(submission.verdict).bg,
                  getVerdict(submission.verdict).border
                )}
              >
                <div className="flex items-center gap-3">
                  <span className={getVerdict(submission.verdict).color}>
                    {getVerdict(submission.verdict).icon}
                  </span>
                  <div>
                    <p
                      className={cn(
                        "text-lg font-bold",
                        getVerdict(submission.verdict).color
                      )}
                    >
                      {getVerdict(submission.verdict).label}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {submission.passed}/{submission.total} ta test o'tdi
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 text-sm sm:ml-auto sm:text-right">
                  <div>
                    <p className="text-[10px] font-medium uppercase text-neutral-400">
                      Vaqt
                    </p>
                    <p className="font-semibold text-neutral-700">
                      {formatTime(submission.time)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] font-medium uppercase text-neutral-400">
                      Xotira
                    </p>
                    <p className="font-semibold text-neutral-700">
                      {formatMemory(submission.memory)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] font-medium uppercase text-neutral-400">
                      Til
                    </p>
                    <p className="font-semibold text-neutral-700">
                      {submission.language?.name || "—"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Progress */}
              {submission.total > 0 && (
                <div>
                  <div className="mb-1 flex justify-between text-xs text-neutral-500">
                    <span>Testlar natijasi</span>
                    <span className="font-medium">
                      {Math.round((submission.passed / submission.total) * 100)}%
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-500",
                        submission.passed === submission.total
                          ? "bg-emerald-500"
                          : "bg-red-400"
                      )}
                      style={{
                        width: `${(submission.passed / submission.total) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Meta Grid */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MetaCard label="Foydalanuvchi" value={submission.user} />
                <MetaCard label="XP" value={`+${submission.xp}`} />
                <MetaCard
                  label="Sana"
                  value={formatDateTime(submission.submitted_at || "")}
                />
                <MetaCard
                  label="Verdict"
                  value={submission.verdict}
                  highlight={submission.status ? "success" : "error"}
                />
              </div>

              {/* Code */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="flex items-center gap-1.5 text-sm font-semibold text-neutral-700">
                    <Terminal className="size-4" />
                    Yuborilgan kod
                  </h3>
                  <button
                    onClick={handleCopyCode}
                    className="flex items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-2.5 py-1 text-xs text-neutral-500 transition-colors hover:bg-neutral-50"
                  >
                    {copied ? (
                      <Check className="size-3 text-emerald-500" />
                    ) : (
                      <Copy className="size-3" />
                    )}
                    {copied ? "Nusxa olindi" : "Nusxa olish"}
                  </button>
                </div>
                <div className="relative">
                  <pre className="max-h-64 overflow-auto rounded-lg border border-neutral-200 bg-neutral-900 p-4 font-mono text-xs leading-relaxed text-neutral-100">
                    <code>{submission.code || "Kod mavjud emas"}</code>
                  </pre>
                </div>
              </div>

              {/* Test Results — Debug Section */}
              {submission.test_results && submission.test_results.length > 0 && (
                <div className="space-y-3">
                  <h3 className="flex items-center gap-1.5 text-sm font-semibold text-neutral-700">
                    <Bug className="size-4 text-orange-500" />
                    Test natijalari (Debug)
                  </h3>

                  {/* Test Grid */}
                  <div className="flex flex-wrap gap-2">
                    {submission.test_results.map((test) => (
                      <button
                        key={test.idx}
                        onClick={() => toggleTest(test.idx)}
                        className={cn(
                          "flex size-8 items-center justify-center rounded-lg text-xs font-bold transition-all",
                          test.ok
                            ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                            : "bg-red-100 text-red-700 hover:bg-red-200",
                          expandedTest === test.idx &&
                            "ring-2 ring-offset-1 ring-orange-400"
                        )}
                        title={`Test #${test.idx} — ${test.verdict || (test.ok ? "AC" : "FAIL")}`}
                      >
                        {test.idx}
                      </button>
                    ))}
                  </div>

                  {/* Expanded Test Detail */}
                  {expandedTest !== null && (
                    <TestDebugCard
                      test={
                        submission.test_results.find((t) => t.idx === expandedTest)!
                      }
                    />
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

function TestDebugCard({ test }: { test: SubmissionTestResult }) {
  const verdict = getVerdict(test.verdict || (test.ok ? "AC" : "WA"));

  return (
    <div
      className={cn(
        "animate-in fade-in slide-in-from-top-2 rounded-xl border p-4 duration-200",
        verdict.bg,
        verdict.border
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={verdict.color}>{verdict.icon}</span>
          <span className={cn("text-sm font-bold", verdict.color)}>
            Test #{test.idx} — {verdict.label}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-neutral-500">
          {test.cpu_time != null && (
            <span className="tabular-nums">{test.cpu_time} ms</span>
          )}
          {test.memory != null && (
            <span className="tabular-nums">{formatMemory(test.memory)}</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <DebugField label="Input" value={test.input || "(bo'sh)"} />
        <DebugField label="Kutilgan (Expected)" value={test.expected || "(bo'sh)"} />
        <DebugField
          label="Sizning javob (Output)"
          value={test.output || "(bo'sh)"}
          highlight={test.ok ? "success" : "error"}
        />
        {test.stderr && (
          <DebugField
            label="Xatolik (Stderr)"
            value={test.stderr}
            highlight="error"
            className="sm:col-span-2"
          />
        )}
      </div>
    </div>
  );
}

function DebugField({
  label,
  value,
  highlight,
  className,
}: {
  label: string;
  value: string;
  highlight?: "success" | "error";
  className?: string;
}) {
  const bgClass =
    highlight === "success"
      ? "bg-emerald-100/40 text-emerald-900"
      : highlight === "error"
      ? "bg-red-100/40 text-red-900"
      : "bg-white/60 text-neutral-800";

  return (
    <div className={className}>
      <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
        {label}
      </span>
      <pre
        className={cn(
          "max-h-32 overflow-auto rounded-lg border border-black/5 p-2.5 font-mono text-[11px] leading-relaxed",
          bgClass
        )}
      >
        {value}
      </pre>
    </div>
  );
}

function MetaCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: "success" | "error";
}) {
  const valueClass =
    highlight === "success"
      ? "text-emerald-600"
      : highlight === "error"
      ? "text-red-600"
      : "text-neutral-800";

  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
      <p className="text-[10px] font-medium uppercase tracking-wide text-neutral-400">
        {label}
      </p>
      <p className={cn("mt-0.5 text-sm font-semibold", valueClass)}>{value}</p>
    </div>
  );
}