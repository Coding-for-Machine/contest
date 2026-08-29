"use client";

import { useState } from "react";
import type { RunResponse, RunResultItem, TestCase } from "@/lib/problems/types";
import { formatMemory } from "@/lib/problems/utils";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Server,
  Play,
  Terminal,
  Copy,
  Check,
  Info,
} from "lucide-react";

type Tab = "testcase" | "result";

interface TestPanelProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  runResults: RunResponse | null;
  isRunning: boolean;
  isSubmitting?: boolean;
  error: string | null;
  exam: TestCase[];
}

const STATUS_CONFIG: Record<
  string,
  { icon: React.ReactNode; label: string; color: string }
> = {
  AC: {
    icon: <CheckCircle2 className="size-4" />,
    label: "Accepted",
    color: "text-emerald-600 bg-emerald-50 border-emerald-200",
  },
  WA: {
    icon: <XCircle className="size-4" />,
    label: "Wrong Answer",
    color: "text-red-600 bg-red-50 border-red-200",
  },
  TLE: {
    icon: <Clock className="size-4" />,
    label: "Time Limit",
    color: "text-amber-600 bg-amber-50 border-amber-200",
  },
  MLE: {
    icon: <AlertTriangle className="size-4" />,
    label: "Memory Limit",
    color: "text-purple-600 bg-purple-50 border-purple-200",
  },
  RE: {
    icon: <AlertTriangle className="size-4" />,
    label: "Runtime Error",
    color: "text-orange-600 bg-orange-50 border-orange-200",
  },
  "Server Error": {
    icon: <Server className="size-4" />,
    label: "Server Error",
    color: "text-neutral-600 bg-neutral-50 border-neutral-200",
  },
};

export function TestPanel({
  activeTab,
  onTabChange,
  runResults,
  isRunning,
  isSubmitting,
  error,
  exam,
}: TestPanelProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 border-b border-neutral-200">
        <TabButton
          active={activeTab === "testcase"}
          onClick={() => onTabChange("testcase")}
          icon={<Terminal className="size-3" />}
          label="Sinov Qutisi"
        />
        <TabButton
          active={activeTab === "result"}
          onClick={() => onTabChange("result")}
          icon={<Play className="size-3" />}
          label="Sinov Natijasi"
        />
      </div>

      <div className="flex-1 overflow-auto p-4">
        {activeTab === "testcase" && <TestCaseTab exam={exam} />}
        {activeTab === "result" && (
          <ResultTab
            runResults={runResults}
            isRunning={isRunning}
            isSubmitting={isSubmitting}
            error={error}
          />
        )}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-medium transition-colors ${
        active
          ? "border-orange-500 text-orange-600"
          : "border-transparent text-neutral-500 hover:text-neutral-700"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function TestCaseTab({ exam }: { exam: TestCase[] }) {
  const [activeCase, setActiveCase] = useState(0);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  if (exam.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-neutral-400">
        <p className="text-sm">Namuna testlar mavjud emas</p>
      </div>
    );
  }

  const current = exam[activeCase];

  const copy = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 1500);
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {exam.map((tc, i) => (
          <button
            key={tc.id}
            onClick={() => setActiveCase(i)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              activeCase === i
                ? "bg-neutral-800 text-white"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
            }`}
          >
            Case {i + 1}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        <TestField
          label="Kirish (input)"
          value={current.input}
          onCopy={() => copy(current.input, `in-${current.id}`)}
          copied={copiedField === `in-${current.id}`}
        />
        <TestField
          label="Kutilgan chiqish (output)"
          value={current.output}
          onCopy={() => copy(current.output, `out-${current.id}`)}
          copied={copiedField === `out-${current.id}`}
        />
        {current.explanation && (
          <p className="text-xs leading-relaxed text-neutral-500">
            <span className="font-medium text-neutral-700">Izoh:</span>{" "}
            {current.explanation}
          </p>
        )}
      </div>
    </div>
  );
}

function TestField({
  label,
  value,
  onCopy,
  copied,
}: {
  label: string;
  value: string;
  onCopy: () => void;
  copied: boolean;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wide text-neutral-400">
          {label}
        </span>
        <button
          onClick={onCopy}
          className="text-neutral-400 transition-colors hover:text-neutral-600"
          aria-label="Nusxa olish"
        >
          {copied ? (
            <Check className="size-3.5 text-emerald-500" />
          ) : (
            <Copy className="size-3.5" />
          )}
        </button>
      </div>
      <pre className="overflow-x-auto rounded-lg border border-neutral-200 bg-white p-3 font-mono text-xs text-neutral-800">
        {value}
      </pre>
    </div>
  );
}

function ResultTab({
  runResults,
  isRunning,
  isSubmitting,
  error,
}: {
  runResults: RunResponse | null;
  isRunning: boolean;
  isSubmitting?: boolean;
  error: string | null;
}) {
  if (isSubmitting) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-neutral-400">
        <div className="size-6 animate-spin rounded-full border-2 border-neutral-300 border-t-orange-500" />
        <p className="text-xs">Yechim tekshirilmoqda...</p>
        <p className="text-[10px] text-neutral-400">Natija alohida oynada ko'rsatiladi</p>
      </div>
    );
  }

  if (isRunning) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-neutral-400">
        <div className="size-6 animate-spin rounded-full border-2 border-neutral-300 border-t-orange-500" />
        <p className="text-xs">Kod ishga tushirilmoqda...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3">
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-xs font-medium text-red-600">Xatolik</p>
          <p className="mt-1 text-xs text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  if (!runResults) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-neutral-400">
        <Play className="size-8 opacity-40" />
        <p className="text-xs">Avval kodingizni ishga tushirishingiz kerak</p>
      </div>
    );
  }

  if (runResults.status === "error") {
    return (
      <div className="space-y-3">
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-xs font-medium text-red-600">Xatolik</p>
          <p className="mt-1 text-xs text-red-500">{runResults.message}</p>
        </div>
      </div>
    );
  }

  if (runResults.status === "input_required") {
    return (
      <div className="space-y-3">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs font-medium text-amber-700">
            Qo'shimcha input talab qilinmoqda
          </p>
          <p className="mt-1 text-xs text-amber-600">
            Console paneliga o'tib input kiriting
          </p>
          {runResults.partial_output && (
            <pre className="mt-2 rounded bg-white p-2 text-xs text-neutral-700">
              {runResults.partial_output}
            </pre>
          )}
        </div>
      </div>
    );
  }

  const allPassed = runResults.results.every((r) => r.status === "AC");

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {allPassed ? (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
            <CheckCircle2 className="size-4" />
            Barcha testlar o'tdi ({runResults.results.length}/
            {runResults.results.length})
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-red-600">
            <XCircle className="size-4" />
            {runResults.results.filter((r) => r.status !== "AC").length} ta
            testda xato
          </span>
        )}
      </div>

      <div className="space-y-3">
        {runResults.results.map((res) => (
          <ResultCard key={res.index} result={res} />
        ))}
      </div>
    </div>
  );
}

function ResultCard({ result }: { result: RunResultItem }) {
  const config = STATUS_CONFIG[result.status] || STATUS_CONFIG["Server Error"];

  return (
    <div className={`rounded-lg border p-3 ${config.color}`}>
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {config.icon}
          <span className="text-xs font-semibold">
            Test #{result.index} — {config.label}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs opacity-80">
          {result.cpu_time != null && <span>{result.cpu_time} ms</span>}
          {result.memory != null && <span>{formatMemory(result.memory)}</span>}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <Field label="Input" value={result.input} />
        <Field label="Kutilgan" value={result.expected_output} />
        <Field
          label="Sizning javob"
          value={result.output || "(bo'sh)"}
          highlight={result.status === "AC" ? "success" : "error"}
        />
      </div>

      {result.message && (
        <div className="mt-2 rounded bg-white/60 p-2">
          <p className="font-mono text-[11px] text-red-600">{result.message}</p>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: "success" | "error";
}) {
  const bgClass =
    highlight === "success"
      ? "bg-emerald-100/50 text-emerald-800"
      : highlight === "error"
      ? "bg-red-100/50 text-red-800"
      : "bg-white/50 text-neutral-700";

  return (
    <div>
      <span className="text-[10px] font-medium uppercase opacity-70">
        {label}
      </span>
      <pre
        className={`mt-0.5 overflow-x-auto rounded p-2 font-mono text-[11px] ${bgClass}`}
      >
        {value}
      </pre>
    </div>
  );
}