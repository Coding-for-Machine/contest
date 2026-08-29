"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, AlertTriangle, Menu, ArrowLeft } from "lucide-react";
import Link from "next/link";
import confetti from "canvas-confetti";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import {
  fetchLectureClient,
  fetchQuizClient,
  fetchLessonProblemPreviewClient,
  LessonApiError,
} from "@/lib/lesson/api";

import {
  selectionToSearchParams,
  type LessonSelection,
  type LessonSummary,
  type LectureDetail,
  type QuizDetail,
  type LessonProblemDetail,
} from "@/lib/lesson/types";

import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";

import { LectureView } from "./lecture-view";
import { LessonProblemWorkspace } from "./lesson-problem-workspace";
import { QuizView } from "./quiz-view";
import { LessonSidebar } from "./lesson-sidebar";
import { LessonCompleteModal } from "./lesson-complete-modal";

type ContentState =
  | { type: "lecture"; data: LectureDetail }
  | { type: "problem"; data: LessonProblemDetail }
  | { type: "quiz"; data: QuizDetail }
  | { type: "none" };

interface LessonDetailShellProps {
  lessonSlug: string;
  courseSlug?: string;
  initialLesson: LessonSummary;
  initialSelection: LessonSelection;
  initialContent: ContentState;
  nextLessonHref?: string | null;
}

function buildUrl(
  courseSlug: string | undefined,
  lessonSlug: string,
  sel: LessonSelection
) {
  const params = new URLSearchParams(selectionToSearchParams(sel));
  const qs = params.toString();

  const base = courseSlug
    ? `/courses/${courseSlug}/lesson/${lessonSlug}`
    : `/lesson/${lessonSlug}`;

  return `${base}${qs ? `?${qs}` : ""}`;
}

function parseSelectionFromLocation(
  lesson: LessonSummary
): LessonSelection {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  const ref = params.get("ref");

  if (tab === "lecture" && ref) {
    const item = lesson.lecs.find((x) => x.s === ref);
    if (item) return { type: "lecture", slug: item.s };
  }

  if (tab === "problem" && ref) {
    const item = lesson.probs.find((x) => x.s === ref);
    if (item) return { type: "problem", slug: item.s };
  }

  if (tab === "quiz" && ref) {
    const item = lesson.qs.find((x) => String(x.id) === ref);
    if (item) return { type: "quiz", id: item.id };
  }

  return { type: "none" };
}

function taskConfetti() {
  confetti({
    particleCount: 45,
    spread: 55,
    startVelocity: 32,
    origin: { y: 0.75 },
    colors: ["#D9AE55", "#ffffff", "#22c55e"],
  });
}

const CONTENT_TITLES: Record<ContentState["type"], string> = {
  lecture: "Ma'ruza",
  problem: "Masala",
  quiz: "Savol",
  none: "Dars",
};

export function LessonDetailShell({
  lessonSlug,
  courseSlug,
  initialLesson,
  initialSelection,
  initialContent,
  nextLessonHref = null,
}: LessonDetailShellProps) {
  const [lesson, setLesson] = useState(initialLesson);
  const [selection, setSelection] = useState(initialSelection);
  const [content, setContent] = useState<ContentState>(initialContent);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionXp, setSessionXp] = useState(0);
  const [showCompleteModal, setShowCompleteModal] = useState(false);

  const prevCompletedRef = useRef(initialLesson.us.done);

  const loadContent = useCallback(
    async (sel: LessonSelection, replaceHistory = false) => {
      setIsLoading(true);
      setError(null);

      try {
        switch (sel.type) {
          case "lecture": {
            const data = await fetchLectureClient(
              lessonSlug,
              sel.slug
            );

            setContent({
              type: "lecture",
              data,
            });

            break;
          }

          case "problem": {
            const data =
              await fetchLessonProblemPreviewClient(
                lessonSlug,
                sel.slug
              );

            setContent({
              type: "problem",
              data,
            });

            break;
          }

          case "quiz": {
            const data = await fetchQuizClient(
              lessonSlug,
              sel.id
            );

            setContent({
              type: "quiz",
              data,
            });

            break;
          }

          default:
            setContent({ type: "none" });
        }

        setSelection(sel);

        const url = buildUrl(
          courseSlug,
          lessonSlug,
          sel
        );

        if (replaceHistory) {
          window.history.replaceState(null, "", url);
        } else {
          window.history.pushState(null, "", url);
        }
      } catch (err) {
        const message =
          err instanceof LessonApiError
            ? err.message
            : "Kontent yuklanmadi";

        setError(message);
        toast.error(message);
      } finally {
        setIsLoading(false);
      }
    },
    [lessonSlug, courseSlug]
  );

  useEffect(() => {
    const handler = () => {
      const sel = parseSelectionFromLocation(lesson);
      loadContent(sel, true);
    };

    window.addEventListener("popstate", handler);

    return () => {
      window.removeEventListener("popstate", handler);
    };
  }, [lesson, loadContent]);

  useEffect(() => {
    if (lesson.us.done && !prevCompletedRef.current) {
      setShowCompleteModal(true);
    }

    prevCompletedRef.current = lesson.us.done;
  }, [lesson.us.done]);

  function handleSelect(sel: LessonSelection) {
    if (isLoading) return;

    const same =
      (sel.type === "lecture" &&
        selection.type === "lecture" &&
        sel.slug === selection.slug) ||
      (sel.type === "problem" &&
        selection.type === "problem" &&
        sel.slug === selection.slug) ||
      (sel.type === "quiz" &&
        selection.type === "quiz" &&
        sel.id === selection.id);

    if (same) return;

    loadContent(sel);
  }

  function handleTaskCompleted(
    kind: "lecture" | "quiz" | "problem",
    id: string | number,
    xp: number
  ) {
    let didChange = false;

    setLesson((prev) => {
      let changed = false;

      const lectures =
        kind === "lecture"
          ? prev.lecs.map((item) =>
              item.s === id
                ? ((changed = true),
                  {
                    ...item,
                    done: true,
                  })
                : item
            )
          : prev.lecs;

      const questions =
        kind === "quiz"
          ? prev.qs.map((item) =>
              item.id === id
                ? ((changed = true),
                  {
                    ...item,
                    done: true,
                  })
                : item
            )
          : prev.qs;

      const problems =
        kind === "problem"
          ? prev.probs.map((item) =>
              item.s === id
                ? ((changed = true),
                  {
                    ...item,
                    done: true,
                  })
                : item
            )
          : prev.probs;

      if (!changed) return prev;

      didChange = true;

      const finished = Math.min(
        prev.us.ft + 1,
        prev.tk
      );

      return {
        ...prev,
        lecs: lectures,
        qs: questions,
        probs: problems,
        us: {
          ...prev.us,
          ft: finished,
          done: finished >= prev.tk,
        },
      };
    });

    if (!didChange) return;

    if (xp > 0) {
      setSessionXp((prev) => prev + xp);

      toast.success(
        `+${xp} XP qo'lga kiritdingiz!`,
        {
          icon: "🎉",
        }
      );
    }

    taskConfetti();
  }

  const backToCourseHref = courseSlug
    ? `/courses/${courseSlug}`
    : "/courses";

  return (
    <SidebarProvider>
      <LessonSidebar
        lesson={lesson}
        selection={selection}
        onSelect={handleSelect}
        isLoading={isLoading}
        courseSlug={courseSlug}
      />

      <SidebarInset className="min-h-[calc(100vh-3.5rem)] bg-white">
        {/* Mobile Top Bar */}
        <div className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-1 border-b border-black/10 bg-white/90 px-4 backdrop-blur-md md:hidden">
          <SidebarTrigger className="size-9 rounded-lg text-black/60 hover:bg-black/5 hover:text-black">
            <Menu className="size-5" />
          </SidebarTrigger>

          <span className="truncate text-sm font-medium text-black/90">
            {CONTENT_TITLES[content.type]}
          </span>
        </div>

        {/* Desktop Header */}
        <div className="hidden h-14 shrink-0 items-center justify-between border-b border-black/10 bg-white px-6 md:flex">
          <div className="flex items-center gap-3">
            <Link
              href={backToCourseHref}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-black/50 transition hover:bg-black/5 hover:text-black"
            >
              <ArrowLeft className="size-4" />
              Kursga qaytish
            </Link>

            <div className="h-4 w-px bg-black/10" />

            <span className="text-sm font-medium text-black/80">
              {lesson.t}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="h-2 w-24 overflow-hidden rounded-full bg-black/10">
              <div
                className="h-full rounded-full bg-[#D9AE55] transition-all"
                style={{
                  width: `${
                    lesson.tk > 0
                      ? (lesson.us.ft / lesson.tk) * 100
                      : 0
                  }%`,
                }}
              />
            </div>

            <span className="text-xs tabular-nums text-black/40">
              {lesson.us.ft}/{lesson.tk}
            </span>
          </div>
        </div>

        <main
          className={
            content.type === "problem"
              ? "relative min-h-0 flex-1 overflow-hidden bg-white p-2"
              : "relative min-h-0 flex-1 overflow-y-auto bg-white px-2 py-2 sm:px-4 sm:py-4"
          }
        >
          {isLoading && (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/80 backdrop-blur-sm">
              <Loader2 className="size-8 animate-spin text-[#D9AE55]" />
            </div>
          )}

          {error && (
            <div className="mx-auto flex max-w-xl items-start gap-3 rounded-xl border border-red-500/20 bg-red-50 p-4 text-sm text-red-500">
              <AlertTriangle className="mt-0.5 size-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!error && content.type === "lecture" && (
            <LectureView
              key={content.data.id}
              lessonSlug={lessonSlug}
              lectureSlug={
                selection.type === "lecture"
                  ? selection.slug
                  : ""
              }
              lecture={content.data}
              onCompleted={(xp) => {
                if (selection.type === "lecture") {
                  handleTaskCompleted(
                    "lecture",
                    selection.slug,
                    xp
                  );
                }
              }}
            />
          )}

          {!error && content.type === "problem" && (
            <div className="h-full min-h-0">
              <LessonProblemWorkspace
                key={content.data.id}
                lessonSlug={lessonSlug}
                problem={content.data}
                onSolved={(xp) => {
                  if (selection.type === "problem") {
                    handleTaskCompleted(
                      "problem",
                      selection.slug,
                      xp
                    );
                  }
                }}
              />
            </div>
          )}

          {!error && content.type === "quiz" && (
            <QuizView
              key={content.data.id}
              lessonSlug={lessonSlug}
              questionId={
                selection.type === "quiz"
                  ? selection.id
                  : 0
              }
              quiz={content.data}
              onCompleted={(xp) => {
                if (selection.type === "quiz") {
                  handleTaskCompleted(
                    "quiz",
                    selection.id,
                    xp
                  );
                }
              }}
            />
          )}

          {!error && content.type === "none" && (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-black/30">
              <div className="flex size-16 items-center justify-center rounded-2xl border border-black/10 bg-black/[0.03]">
                <span className="text-2xl">📚</span>
              </div>

              <p className="text-sm">
                Bu darsda hali kontent yo&apos;q
              </p>
            </div>
          )}
        </main>
      </SidebarInset>

      <LessonCompleteModal
        open={showCompleteModal}
        onClose={() => setShowCompleteModal(false)}
        lessonTitle={lesson.t}
        totalTasks={lesson.tk}
        earnedXp={sessionXp}
        nextHref={nextLessonHref}
      />

      <ToastContainer
        position="top-center"
        autoClose={2500}
        hideProgressBar
        newestOnTop
        closeOnClick
        theme="light"
        toastClassName="!rounded-xl !text-sm !bg-white !text-black !border !border-black/10"
      />
    </SidebarProvider>
  );
}