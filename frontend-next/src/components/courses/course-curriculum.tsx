"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import {
  ChevronDown,
  PlayCircle,
  FileText,
  HelpCircle,
  Lock,
  CheckCircle2,
  CircleDot,
  Circle,
  Award,
  XCircle,
  RotateCcw,
  BookOpen,
} from "lucide-react";
import type { CourseModule } from "@/lib/types/course";

interface CourseCurriculumProps {
  modules: CourseModule[];
  courseSlug: string;
  isPaid: boolean;
  isLoggedIn: boolean;
  isFree: boolean;
}

function getLessonIcon(title: string) {
  const t = title.toLowerCase();

  if (t.includes("ma'ruza") || t.includes("lecture")) {
    return <FileText className="size-4 text-slate-400" />;
  }

  return <PlayCircle className="size-4 text-slate-400" />;
}

export function CourseCurriculum({
  modules,
  courseSlug,
  isPaid,
  isLoggedIn,
  isFree,
}: CourseCurriculumProps) {
  const [openModules, setOpenModules] = useState<Set<number>>(
    new Set(modules.length > 0 ? [modules[0].id] : [])
  );

  const toggleModule = (id: number) => {
    setOpenModules((prev) => {
      const next = new Set(prev);

      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }

      return next;
    });
  };

  if (modules.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
        <div className="flex size-12 items-center justify-center rounded-full bg-slate-50">
          <BookOpen className="size-6 text-slate-400" />
        </div>

        <p className="mt-2 text-sm font-semibold text-slate-700">
          Kurs dasturi hali e'lon qilinmagan
        </p>

        <p className="text-xs text-slate-400">
          Modullar tayyor bo'lgach, shu yerda ko'rinadi
        </p>
      </div>
    );
  }

  // Anonim userlar uchun backend o'zi lock qiladi.
  // Login qilgan + pullik + sotib olmagan -> to'liq qulf.
  const isPaywallLocked = isLoggedIn && !isPaid && !isFree;

  return (
    <div className="flex flex-col gap-3">
      {modules.map((modul, modIdx) => {
        const isOpen = openModules.has(modul.id);
        const ms = modul.user_status;

        const modCompletedLessons = ms?.completed_lessons ?? 0;
        const modCompletedTests = ms?.completed_tests ?? 0;

        const modTotalLessons = modul.total_lessons;
        const modTotalTests = modul.total_tests;

        const modTotalTasks = modTotalLessons + modTotalTests;
        const modFinishedTasks =
          modCompletedLessons + modCompletedTests;

        const modulePercent =
          modTotalTasks > 0
            ? Math.round((modFinishedTasks / modTotalTasks) * 100)
            : 0;

        const isModuleCompleted = ms?.is_completed ?? false;

        const isModuleProgressLocked =
          !isPaywallLocked && modul.locked;

        const isModuleLocked =
          isPaywallLocked || isModuleProgressLocked;

        const allLessonsDone =
          modTotalLessons === 0 ||
          modCompletedLessons >= modTotalLessons;

        const isTestLocked =
          isModuleLocked || !allLessonsDone;

        return (
          <div
            key={modul.id}
            className={[
              "overflow-hidden rounded-2xl border bg-white",
              "border-slate-200 shadow-sm",
              "transition-all duration-200",
              isOpen
                ? "shadow-md shadow-slate-200/50"
                : "hover:border-slate-300 hover:shadow-md",
            ].join(" ")}
          >
            {/* MODULE HEADER */}
            <button
              onClick={() => toggleModule(modul.id)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-slate-50 sm:px-6"
            >
              <div className="flex min-w-0 items-center gap-4">
                {/* Number */}
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[#B88A2D]/10">
                  <span className="font-mono text-xs font-bold text-[#A97920]">
                    {String(modIdx + 1).padStart(2, "0")}
                  </span>
                </div>

                <div className="min-w-0 flex-1">
                  <h3
                    className={[
                      "flex items-center gap-2 text-sm font-bold",
                      isModuleLocked
                        ? "text-slate-400"
                        : "text-slate-900",
                    ].join(" ")}
                  >
                    <span className="truncate">{modul.title}</span>

                    {isModuleLocked && (
                      <Lock className="size-3.5 shrink-0 text-slate-400" />
                    )}
                  </h3>

                  <p className="mt-1 text-xs text-slate-400">
                    {modTotalLessons} dars
                    {modTotalTests > 0
                      ? ` · ${modTotalTests} test`
                      : ""}

                    {isLoggedIn && isPaid && ms
                      ? ` · ${modFinishedTasks}/${modTotalTasks} bajarildi`
                      : ""}

                    {isPaywallLocked
                      ? " · sotib olish talab qilinadi"
                      : isModuleProgressLocked
                        ? " · oldingi modulni tugating"
                        : ""}
                  </p>
                </div>
              </div>

              {/* RIGHT SIDE */}
              <div className="flex shrink-0 items-center gap-3">
                {isLoggedIn &&
                  isPaid &&
                  modTotalTasks > 0 && (
                    <div className="hidden items-center gap-2 sm:flex">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-[#C89B3C] transition-all duration-500"
                          style={{
                            width: `${modulePercent}%`,
                          }}
                        />
                      </div>

                      <span className="w-8 text-right text-[11px] font-mono font-medium text-slate-400">
                        {modulePercent}%
                      </span>
                    </div>
                  )}

                {isModuleCompleted && (
                  <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
                )}

                <ChevronDown
                  className={[
                    "size-4 shrink-0 text-slate-400",
                    "transition-transform duration-200",
                    isOpen ? "rotate-180" : "",
                  ].join(" ")}
                />
              </div>
            </button>

            {/* LESSONS */}
            {isOpen && (
              <div className="border-t border-slate-100">
                {modul.lessons.map((lesson) => {
                  const isLocked =
                    isModuleLocked || lesson.locked;

                  const isCompleted =
                    lesson.user_status?.is_completed ?? false;

                  const finishedTasks =
                    lesson.user_status?.finished_tasks ?? 0;

                  const isInProgress =
                    !isCompleted &&
                    !isLocked &&
                    finishedTasks > 0;

                  return (
                    <div
                      key={lesson.id}
                      className={[
                        "group flex items-center gap-3",
                        "border-b border-slate-100 px-5 py-3",
                        "last:border-0 sm:px-6",
                        isLocked
                          ? "bg-slate-50/50 opacity-60"
                          : "transition-colors hover:bg-slate-50",
                      ].join(" ")}
                    >
                      {/* STATUS */}
                      <div className="flex size-6 shrink-0 items-center justify-center">
                        {isCompleted ? (
                          <CheckCircle2 className="size-4 text-emerald-500" />
                        ) : isLocked ? (
                          <Lock className="size-3.5 text-slate-400" />
                        ) : isInProgress ? (
                          <CircleDot className="size-4 text-[#B88A2D]" />
                        ) : (
                          <Circle className="size-4 text-slate-300" />
                        )}
                      </div>

                      {/* LESSON */}
                      <div className="flex min-w-0 flex-1 items-center gap-2">
                        {getLessonIcon(lesson.title)}

                        {isLocked ? (
                          <span className="truncate text-sm text-slate-500">
                            {lesson.title}
                          </span>
                        ) : (
                          <Link
                            href={`/courses/${courseSlug}/lesson/${lesson.slug}`}
                            className="truncate text-sm font-medium text-slate-700 transition-colors hover:text-[#A97920]"
                          >
                            {lesson.title}
                          </Link>
                        )}

                        {isCompleted && (
                          <span className="hidden shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600 sm:inline-flex">
                            Tugallangan
                          </span>
                        )}

                        {!isLocked && isInProgress && (
                          <span className="shrink-0 rounded-full bg-[#C89B3C]/10 px-2 py-0.5 text-[10px] font-semibold text-[#A97920]">
                            {finishedTasks}/{lesson.total_tasks}
                          </span>
                        )}
                      </div>

                      {/* ORDER */}
                      <span className="shrink-0 font-mono text-[10px] text-slate-300">
                        #{lesson.order}
                      </span>
                    </div>
                  );
                })}

                {/* TEST */}
                {modul.test && (
                  <TestRow
                    courseSlug={courseSlug}
                    test={modul.test}
                    locked={isTestLocked}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ==================== MODUL TESTI ==================== */

function TestRow({
  courseSlug,
  test,
  locked,
}: {
  courseSlug: string;
  test: NonNullable<CourseModule["test"]>;
  locked: boolean;
}) {
  const result = test.result;
  const passed = result?.passed ?? null;
  const attempted = result?.attempted ?? false;

  let icon: ReactNode;
  let badge: ReactNode = null;

  let actionLabel: ReactNode = "Testni boshlash";

  if (locked) {
    icon = <Lock className="size-3.5 text-slate-400" />;
  } else if (passed === true) {
    icon = (
      <CheckCircle2 className="size-4 text-emerald-500" />
    );

    badge = (
      <span className="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
        O'tdi · {result?.score_pct}%
      </span>
    );

    actionLabel = (
      <>
        <RotateCcw className="size-3" />
        Natijani ko'rish
      </>
    );
  } else if (attempted && passed === false) {
    icon = <XCircle className="size-4 text-red-500" />;

    badge = (
      <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-600">
        O'tmadi · {result?.score_pct}%
      </span>
    );

    actionLabel = (
      <>
        <RotateCcw className="size-3" />
        Qayta urinish
      </>
    );
  } else {
    icon = <HelpCircle className="size-4 text-slate-400" />;
  }

  const body = (
    <>
      <div className="flex size-6 shrink-0 items-center justify-center">
        {icon}
      </div>

      <div className="flex min-w-0 flex-1 items-center gap-2">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[#C89B3C]/10">
          <Award className="size-4 text-[#A97920]" />
        </div>

        <span
          className={[
            "truncate text-sm",
            locked
              ? "text-slate-500"
              : "font-semibold text-slate-800",
          ].join(" ")}
        >
          {test.title}
        </span>

        {badge}
      </div>

      {!locked && (
        <span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-[#A97920] transition-colors group-hover:text-[#8F681A]">
          {actionLabel}
        </span>
      )}
    </>
  );

  const rowClass = [
    "group flex items-center gap-3",
    "border-b border-slate-100",
    "bg-[#FFFCF6] px-5 py-3",
    "last:border-0 sm:px-6",
  ].join(" ");

  if (locked) {
    return (
      <div
        className={`${rowClass} opacity-60`}
        title="Avval moduldagi darslarni tugating"
      >
        {body}
      </div>
    );
  }

  return (
    <Link
      href={`/courses/${courseSlug}/test/${test.slug}`}
      className={`${rowClass} transition-colors hover:bg-[#FFF8E9]`}
    >
      {body}
    </Link>
  );
}