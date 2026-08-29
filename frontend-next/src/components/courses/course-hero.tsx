"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Play,
  PlayCircle,
  HelpCircle,
  Users,
  Clock,
  Lock,
  Layers,
  BarChart3,
} from "lucide-react";
import { VideoPlayer } from "@/components/VideoPlayer";
import type { CourseLevel, CourseUserProgress } from "@/lib/types/course";

const LEVEL_LABELS: Record<CourseLevel, string> = {
  beginner: "Boshlang'ich",
  intermediate: "O'rta",
  advanced: "Yuqori",
};

interface CourseHeroProps {
  course: {
    title: string;
    description?: string;
    price: number;
    discount_price?: number | null;
    students?: number;
    level?: CourseLevel;
    total_modules?: number;
    video?: {
      hls_url?: string;
      thumbnail?: string;
      duration?: number | string;
    } | null;
    total_lessons: number;
    total_tests: number;
  };
  isPaid: boolean;
  isLoggedIn: boolean;
  firstLessonSlug?: string;
  courseSlug: string;
  progress?: CourseUserProgress | null;
}

export function CourseHero({
  course,
  isPaid,
  isLoggedIn,
  firstLessonSlug,
  courseSlug,
  progress,
}: CourseHeroProps) {
  const [showVideo, setShowVideo] = useState(false);

  const price = Number(course.price ?? 0);
  const discountPrice = course.discount_price != null ? Number(course.discount_price) : null;
  const currentPrice = discountPrice ?? price;
  const isFree = !currentPrice || currentPrice <= 0;
  const hasVideo = !!course.video?.hls_url;

  const formatDuration = (dur?: number | string) => {
    if (!dur) return null;
    // Backend sekund yoki "MM:SS" formatida yuborishi mumkin
    let mins = 0;
    if (typeof dur === "string") {
      const parts = dur.split(":").map(Number);
      mins = parts.length === 2 ? parts[0] : 0;
    } else {
      mins = Math.floor(dur / 60);
    }
    const h = Math.floor(mins / 60);
    const m = Math.floor(mins % 60);
    return h > 0 ? `${h} soat ${m} daq` : `${m} daq`;
  };

  const durationLabel = formatDuration(course.video?.duration);

  const hasStarted =
    !!progress &&
    (Boolean(progress.started_at) ||
      progress.completed_lessons > 0 ||
      progress.completed_tests > 0);

  let statusLabel: string;
  let statusColor: string;
  if (isPaid && progress?.is_completed) {
    statusLabel = "Tugallandi";
    statusColor = "bg-emerald-500";
  } else if (isPaid) {
    statusLabel = "Sizda mavjud";
    statusColor = "bg-emerald-500";
  } else if (isFree) {
    statusLabel = "Bepul kurs";
    statusColor = "bg-[#D9AE55]";
  } else {
    statusLabel = "Yangi kurs";
    statusColor = "bg-white";
  }

  let primaryHref: string;
  let primaryLabel: string;
  if (isPaid && firstLessonSlug) {
    primaryHref = `/courses/${courseSlug}/lesson/${firstLessonSlug}`;
    primaryLabel = hasStarted ? "Davom ettirish" : "Kursni boshlash";
  } else {
    primaryHref = "#pricing";
    primaryLabel = isFree ? "Bepul yozilish" : "Xarid qilish";
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-4 lg:px-8">
      <div className="overflow-hidden rounded-2xl bg-[#121212] border border-white/10">
        <div className="grid grid-cols-1 items-center gap-10 p-8 sm:p-10 lg:grid-cols-[1.05fr_1fr]">
          {/* Left: text */}
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 px-3 py-1 text-xs font-medium text-white/70">
                <span className={`size-1.5 rounded-full ${statusColor}`} />
                {statusLabel}
              </span>

              {course.level && (
                <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-white/10 px-3 py-1 text-xs font-medium text-white/50">
                  <BarChart3 className="size-3 text-[#D9AE55]" />
                  {LEVEL_LABELS[course.level] ?? course.level}
                </span>
              )}
            </div>

            <h1 className="font-display text-3xl font-bold leading-[1.15] text-white sm:text-4xl lg:text-5xl">
              {course.title}
            </h1>

            {course.description && (
              <p className="max-w-lg text-sm leading-relaxed text-white/50">
                {course.description.replace(/[#*`]/g, "").slice(0, 220)}
                {course.description.length > 220 ? "..." : ""}
              </p>
            )}

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-white/10 pt-5 text-sm text-white/40">
              {typeof course.total_modules === "number" && course.total_modules > 0 && (
                <span className="flex items-center gap-2">
                  <Layers className="size-4 text-[#D9AE55]" />
                  {course.total_modules} modul
                </span>
              )}
              <span className="flex items-center gap-2">
                <PlayCircle className="size-4 text-[#D9AE55]" />
                {course.total_lessons} dars
              </span>
              <span className="flex items-center gap-2">
                <HelpCircle className="size-4 text-[#D9AE55]" />
                {course.total_tests} test
              </span>
              {durationLabel && (
                <span className="flex items-center gap-2">
                  <Clock className="size-4 text-[#D9AE55]" />
                  {durationLabel}
                </span>
              )}
              {typeof course.students === "number" && course.students > 0 && (
                <span className="flex items-center gap-2">
                  <Users className="size-4 text-[#D9AE55]" />
                  {course.students.toLocaleString()}+ o'quvchi
                </span>
              )}
            </div>

            {/* CTA row */}
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={primaryHref}
                className="rounded-lg bg-[#D9AE55] px-6 py-2.5 text-sm font-semibold text-[#121212] transition-opacity hover:opacity-90"
              >
                {primaryLabel}
              </Link>
              <Link
                href="#curriculum"
                className="rounded-lg border border-white/15 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/5"
              >
                Dastur bilan tanishish
              </Link>
            </div>
          </div>

          {/* Right: video */}
          <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black">
            {showVideo && hasVideo ? (
              <VideoPlayer
                src={course.video!.hls_url!}
                poster={course.video?.thumbnail}
                title={course.title}
              />
            ) : (
              <div className="relative aspect-video">
                {course.video?.thumbnail ? (
                  <Image
                    src={course.video.thumbnail}
                    alt={course.title}
                    fill
                    className="object-cover"
                    priority
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <PlayCircle className="size-16 text-white/10" />
                  </div>
                )}

                {hasVideo && (
                  <button
                    onClick={() => setShowVideo(true)}
                    aria-label="Videoni ko'rish"
                    className="absolute left-1/2 top-1/2 flex size-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-[#D9AE55] shadow-xl transition hover:scale-105"
                  >
                    <Play className="ml-1 size-6 fill-[#121212] text-[#121212]" />
                  </button>
                )}

                {!isPaid && !isFree && isLoggedIn && (
                  <div className="absolute right-3 top-3 flex items-center gap-1.5 rounded-full bg-black/70 px-3 py-1.5 text-xs font-medium text-white backdrop-blur">
                    <Lock className="size-3 text-[#D9AE55]" />
                    Sotib olishingiz kerak
                  </div>
                )}

                {durationLabel && (
                  <div className="absolute bottom-3 right-3 rounded-md bg-black/70 px-2 py-1 text-xs text-white">
                    {durationLabel}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}