"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Clock,
  MemoryStick,
  Zap,
  Tag,
  Lightbulb,
  ListChecks,
  Terminal,
  Copy,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { LessonProblemDetail } from "@/lib/lesson/types";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
// NOTE: loyihangizdagi haqiqiy joylashuvga qarab moslashtiring.
import { SubmissionList } from "@/components/problems/submission-list";

type Tab = "description" | "hints" | "challenges" | "submissions";

const DIFFICULTY_STYLES: Record<string, string> = {
  easy: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  hard: "bg-red-50 text-red-700 border-red-200",
};

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "Oson",
  medium: "O'rtacha",
  hard: "Qiyin",
};

interface LessonProblemDescriptionProps {
  problem: LessonProblemDetail;
}

export function LessonProblemDescription({
  problem,
}: LessonProblemDescriptionProps) {
  const [activeTab, setActiveTab] = useState<Tab>("description");

  const hasHints = problem.hints.length > 0;
  const hasChallenges = problem.chall.length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="flex shrink-0 items-center gap-0.5 overflow-x-auto border-b border-neutral-200 bg-white px-1">
        <TabButton
          active={activeTab === "description"}
          onClick={() => setActiveTab("description")}
          label="Tavsif"
        />
        {hasHints && (
          <TabButton
            active={activeTab === "hints"}
            onClick={() => setActiveTab("hints")}
            label="Maslahatlar"
            count={problem.hints.length}
          />
        )}
        {hasChallenges && (
          <TabButton
            active={activeTab === "challenges"}
            onClick={() => setActiveTab("challenges")}
            label="Talablar"
            count={problem.chall.length}
          />
        )}
        <TabButton
          active={activeTab === "submissions"}
          onClick={() => setActiveTab("submissions")}
          label="Taqdimotlar"
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "description" && <DescriptionTab problem={problem} />}
        {activeTab === "hints" && <HintsTab problem={problem} />}
        {activeTab === "challenges" && <ChallengesTab problem={problem} />}
        {activeTab === "submissions" && (
          <div className="p-6">
            <SubmissionList slug={problem.slug} />
          </div>
        )}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative flex shrink-0 items-center gap-1.5 px-4 py-3 text-sm font-medium transition-colors",
        active ? "text-orange-600" : "text-neutral-500 hover:text-neutral-700"
      )}
    >
      {label}
      {typeof count === "number" && (
        <span
          className={cn(
            "flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-semibold tabular-nums",
            active
              ? "bg-orange-100 text-orange-600"
              : "bg-neutral-100 text-neutral-500"
          )}
        >
          {count}
        </span>
      )}
      {active && (
        <span className="absolute bottom-0 left-0 h-0.5 w-full bg-orange-500" />
      )}
    </button>
  );
}

function DescriptionTab({ problem }: { problem: LessonProblemDetail }) {
  const [activeExample, setActiveExample] = useState(0);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const diffStyle = DIFFICULTY_STYLES[problem.dif] || DIFFICULTY_STYLES.easy;
  const diffLabel = DIFFICULTY_LABELS[problem.dif] || problem.dif;

  const handleCopy = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 1500);
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="mb-3 text-2xl font-bold text-neutral-900">
            {problem.title}
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-xs font-semibold",
                diffStyle
              )}
            >
              {diffLabel}
            </span>
            {problem.cate_name && (
              <span className="rounded-full border border-neutral-200 px-2.5 py-0.5 text-xs text-neutral-600">
                {problem.cate_name}
              </span>
            )}
            {problem.tags.map((tag) => (
              <span
                key={tag.id}
                className="inline-flex items-center gap-1 rounded-md bg-neutral-100 px-2 py-1 text-xs text-neutral-600"
              >
                <Tag className="size-3" />
                {tag.name}
              </span>
            ))}
          </div>
        </div>

        {problem.solved && (
          <div className="flex shrink-0 items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-600">
            <CheckCircle2 className="size-4" />
            Yechim topildi
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetaItem
          icon={<Zap className="size-4 text-orange-500" />}
          label="XP"
          value={String(problem.xp)}
        />
        <MetaItem
          icon={<Clock className="size-4 text-blue-500" />}
          label="Vaqt limiti"
          value={`${problem.time_l} s`}
        />
        <MetaItem
          icon={<MemoryStick className="size-4 text-purple-500" />}
          label="Xotira limiti"
          value={`${problem.memory_l} MB`}
        />
        <MetaItem
          icon={<Terminal className="size-4 text-neutral-500" />}
          label="Qabul qilish"
          value={`${problem.acceptance}%`}
        />
      </div>

      {/* Description */}
      <div className="prose prose-neutral max-w-none">
        <MarkdownRenderer content={problem.desc} />
      </div>

      {/* Namuna testlar */}
      {problem.exam.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-900">
            <Terminal className="size-4 text-neutral-500" />
            Namuna testlar
          </h3>

          <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
            <div className="flex border-b border-neutral-200 bg-neutral-50">
              {problem.exam.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveExample(idx)}
                  className={cn(
                    "px-4 py-2 text-xs font-medium transition-colors",
                    activeExample === idx
                      ? "border-b-2 border-orange-500 bg-white text-orange-600"
                      : "text-neutral-500 hover:text-neutral-700"
                  )}
                >
                  Case {idx + 1}
                </button>
              ))}
            </div>

            <div className="p-4">
              {(() => {
                const ex = problem.exam[activeExample];
                if (!ex) return null;
                return (
                  <div className="space-y-3">
                    <DataField
                      label="Kirish (Input)"
                      value={ex.input}
                      onCopy={() => handleCopy(ex.input, `in-${ex.id}`)}
                      copied={copiedField === `in-${ex.id}`}
                    />
                    <DataField
                      label="Chiqish (Output)"
                      value={ex.output}
                      onCopy={() => handleCopy(ex.output, `out-${ex.id}`)}
                      copied={copiedField === `out-${ex.id}`}
                    />
                    {ex.explanation && (
                      <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-3">
                        <p className="mb-1 text-xs font-medium text-amber-800">
                          Izoh
                        </p>
                        <p className="text-sm text-amber-700">
                          {ex.explanation}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function HintsTab({ problem }: { problem: LessonProblemDetail }) {
  if (problem.hints.length === 0) {
    return (
      <EmptyTabState
        icon={<Lightbulb className="size-8" />}
        text="Maslahatlar mavjud emas"
      />
    );
  }

  return (
    <div className="space-y-3 p-6">
      {problem.hints.map((h, i) => (
        <div
          key={h.id}
          className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
        >
          <div className="mb-1.5 flex items-center gap-1.5 font-semibold">
            <Lightbulb className="size-4" />
            Maslahat {i + 1}
          </div>
          <MarkdownRenderer content={h.text} />
        </div>
      ))}
    </div>
  );
}

function ChallengesTab({ problem }: { problem: LessonProblemDetail }) {
  if (problem.chall.length === 0) {
    return (
      <EmptyTabState
        icon={<ListChecks className="size-8" />}
        text="Qo'shimcha talablar mavjud emas"
      />
    );
  }

  return (
    <div className="p-6">
      <ul className="space-y-3">
        {problem.chall.map((c, i) => (
          <li
            key={c.id}
            className="flex gap-3 rounded-xl border border-neutral-200 bg-white p-4"
          >
            <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-orange-100 text-[11px] font-semibold text-orange-600">
              {i + 1}
            </span>
            <div className="text-sm text-neutral-700">
              <MarkdownRenderer content={c.text} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function EmptyTabState({
  icon,
  text,
}: {
  icon: React.ReactNode;
  text: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 py-16 text-neutral-300">
      {icon}
      <p className="text-sm text-neutral-400">{text}</p>
    </div>
  );
}

function MetaItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-3">
      <div className="mb-1 flex items-center gap-1.5 text-xs text-neutral-400">
        {icon}
        {label}
      </div>
      <p className="text-sm font-semibold text-neutral-900">{value}</p>
    </div>
  );
}

function DataField({
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
        <span className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
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
      <pre className="overflow-x-auto rounded-lg border border-neutral-200 bg-neutral-50 p-3 font-mono text-xs text-neutral-800">
        {value}
      </pre>
    </div>
  );
}