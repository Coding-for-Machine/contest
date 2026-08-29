"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Loader2,
  Clock,
  Zap,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { completeLectureClient } from "@/lib/lesson/api";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { VideoPlayer } from "@/components/VideoPlayer";
import { LectureDetail } from "@/lib/lesson/types";

interface LectureViewProps {
  lessonSlug: string;
  lectureSlug: string;
  lecture: LectureDetail;
  onCompleted: (xp: number) => void;
}

export function LectureView({
  lessonSlug,
  lectureSlug,
  lecture,
  onCompleted,
}: LectureViewProps) {
  const [isCompleting, setIsCompleting] = useState(false);
  const [isCompleted, setIsCompleted] = useState(
    lecture.is_completed
  );
  const [error, setError] = useState<string | null>(null);

  const handleComplete = async () => {
    if (isCompleting || isCompleted) return;

    setIsCompleting(true);
    setError(null);

    try {
      const result = await completeLectureClient(
        lessonSlug,
        lectureSlug
      );

      if (result.completed) {
        setIsCompleted(true);
        onCompleted(result.xp);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Xatolik yuz berdi"
      );
    } finally {
      setIsCompleting(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl">
      {/* Header Card */}
      <div className="rounded-2xl border border-black/10 bg-white p-2 shadow-sm sm:p-3">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-[#B88A2D]">
          <BookOpen className="size-4" />
          Ma&apos;ruza
        </div>

        <h1 className="mt-3 text-2xl font-bold text-black sm:text-3xl">
          {lecture.title}
        </h1>

        <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-black/40">
          {lecture.reading_time ? (
            <span className="flex items-center gap-1.5">
              <Clock className="size-4" />
              {lecture.reading_time} daqiqa
            </span>
          ) : null}

          <span className="flex items-center gap-1.5">
            <Zap className="size-4 text-[#D9AE55]" />
            {lecture.xp} XP
          </span>
        </div>
      </div>

      {/* Video */}
      {lecture.video.hls_url && (
        <div className="mt-6 overflow-hidden rounded-2xl border border-black/10 bg-black">
          <VideoPlayer
            src={lecture.video.hls_url}
            poster={lecture.video.thumbnail ?? undefined}
          />
        </div>
      )}

      {/* Body */}
      <div className="mt-8 rounded-2xl border border-black/10 bg-white p-6 shadow-sm sm:p-8">
        <div className="prose prose-neutral max-w-none text-black">
          <MarkdownRenderer content={lecture.body} />
        </div>
      </div>

      {/* Complete Action */}
      <div className="mt-8 flex flex-col gap-5 rounded-2xl border border-black/10 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-black/90">
            {isCompleted
              ? "Ma'ruzani tugatdingiz"
              : "Ma'ruzani tugatdingizmi?"}
          </p>

          <p className="mt-0.5 text-xs text-black/40">
            {isCompleted
              ? "Keyingi vazifaga o'tishingiz mumkin"
              : "Tugatish tugmasini bosing va XP qo'lga kiritiring"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {error && (
            <p className="text-sm text-red-500">
              {error}
            </p>
          )}

          <button
            type="button"
            onClick={handleComplete}
            disabled={isCompleting || isCompleted}
            className={cn(
              "flex h-11 items-center gap-2 rounded-xl px-6 text-sm font-semibold transition-all",
              isCompleted
                ? "cursor-default bg-green-50 text-green-600"
                : "bg-[#D9AE55] text-black hover:bg-[#c49b48] disabled:opacity-60"
            )}
          >
            {isCompleting ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <CheckCircle2 className="size-4" />
            )}

            {isCompleted
              ? "Tugatilgan"
              : "Tugatish"}
          </button>
        </div>
      </div>
    </div>
  );
}