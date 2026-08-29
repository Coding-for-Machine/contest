"use client";

import Link from "next/link";
import {
  ChevronLeft,
  Play,
  Loader2,
  CloudUpload,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LessonProblemNavbarProps {
  lessonSlug: string;
  problemTitle: string;
  solved?: boolean;

  onRun?: () => void;
  onSubmit?: () => void;
  isRunning?: boolean;
  isSubmitting?: boolean;

  /** Darsning masalalar/ma'ruzalar ro'yxatiga qaytish (sidebar'ni ochish o'rniga) */
  onBack?: () => void;
}

export function LessonProblemNavbar({
  lessonSlug,
  problemTitle,
  solved,
  onRun,
  onSubmit,
  isRunning,
  isSubmitting,
  onBack,
}: LessonProblemNavbarProps) {
  return (
    <header className="flex h-12 w-full shrink-0 items-center justify-between gap-2 border-b border-neutral-200 bg-white px-3">
      {/* Chap: darsga qaytish */}
      <div className="flex min-w-0 items-center gap-2">
        {onBack ? (
          <button
            type="button"
            onClick={onBack}
            aria-label="Darsga qaytish"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            <ChevronLeft className="size-[18px]" />
          </button>
        ) : (
          <Link
            href={`/lesson/${lessonSlug}`}
            aria-label="Darsga qaytish"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            <ChevronLeft className="size-[18px]" />
          </Link>
        )}

        <div className="mx-1 hidden h-5 w-px bg-neutral-200 sm:block" />

        <span className="truncate text-sm font-medium text-neutral-700">
          {problemTitle}
        </span>

        {solved && (
          <span className="hidden shrink-0 items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 sm:flex">
            <CheckCircle2 className="size-3" />
            Yechilgan
          </span>
        )}
      </div>

      {/* O'ng: Run / Submit */}
      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={onRun}
          disabled={isRunning || isSubmitting}
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-neutral-50 px-3 text-sm font-medium text-neutral-700 transition-colors",
            "hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {isRunning ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Play className="size-4" />
          )}
          <span className="hidden sm:inline">Yuritish</span>
        </button>

        <button
          type="button"
          onClick={onSubmit}
          disabled={isRunning || isSubmitting}
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-md bg-neutral-900 px-3 text-sm font-medium text-white transition-colors",
            "hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {isSubmitting ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <CloudUpload className="size-4" />
          )}
          <span className="hidden sm:inline">Yuborish</span>
        </button>
      </div>
    </header>
  );
}