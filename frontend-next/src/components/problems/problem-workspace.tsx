"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Scan, Minimize, ChevronLeft, ChevronRight } from "lucide-react";
import type { PanelImperativeHandle } from "react-resizable-panels";
import type { ProblemDetail } from "@/lib/problems/types";
import { getAdjacentProblem, getRandomProblem } from "@/lib/problems/api";
import { DescriptionPanel } from "./description-panel";
import {
  CodeEditorPanel,
  type CodeEditorPanelHandle,
} from "./code-editor-panel";
import { ProblemNavbar } from "./problem-navbar";
import { SubmissionTracker } from "./submission-result-modal";
import { useSubmissionTracker } from "@/hooks/useSubmissionTracker";
import submissionTracker from "@/lib/submissions/tracker"; // ← import qo'shildi
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { cn } from "@/lib/utils";

interface ProblemWorkspaceProps {
  problem: ProblemDetail;
}

type Layout = "split" | "left-full" | "right-full";

const toolbarButtonClass = cn(
  "flex h-7 w-7 items-center justify-center rounded-md text-neutral-400",
  "bg-transparent transition-colors",
  "hover:bg-neutral-100 hover:text-neutral-800",
  "dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
);

export function ProblemWorkspace({ problem }: ProblemWorkspaceProps) {
  const router = useRouter();

  const [isMobile, setIsMobile] = useState(false);
  const [layout, setLayout] = useState<Layout>("split");

  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [isNavigating, setIsNavigating] = useState(false);
  const [hasPrev, setHasPrev] = useState(true);
  const [hasNext, setHasNext] = useState(true);

  const leftPanelRef = useRef<PanelImperativeHandle>(null);
  const rightPanelRef = useRef<PanelImperativeHandle>(null);
  const editorHandleRef = useRef<CodeEditorPanelHandle>(null);

  // === SUBMISSION TRACKER / MODAL ===
  const submission = useSubmissionTracker();
  const [trackerOpen, setTrackerOpen] = useState(false);
  const lastSubmissionId = useRef<string | null>(null);

  // MOUNT: mavjud tracker id'sini "ko'rilgan" deb belgilash
  // (boshqa sahifadan kelganda eski modal ochilmasligi uchun)
  useEffect(() => {
    lastSubmissionId.current = submission?.id ?? null;
  }, []);

  // Yangi submit bo'lganda MODAL ochish (faqat haqiqatan yangi bo'lsa)
  useEffect(() => {
    if (submission?.id && submission.id !== lastSubmissionId.current) {
      lastSubmissionId.current = submission.id;
      setTrackerOpen(true);
    }
  }, [submission?.id]);

  // UNMOUNT: masala sahifasidan chiqishda tracker tozalansin
  useEffect(() => {
    return () => {
      submissionTracker.clear();
    };
  }, []);
  // ===================================

  useEffect(() => {
    const checkWidth = () => setIsMobile(window.innerWidth < 1024);
    checkWidth();
    window.addEventListener("resize", checkWidth);
    return () => window.removeEventListener("resize", checkWidth);
  }, []);

  const applyLayout = (next: Layout) => {
    const left = leftPanelRef.current;
    const right = rightPanelRef.current;
    if (!left || !right) return;

    if (next === "left-full") {
      right.resize("0%");
      left.resize("100%");
    } else if (next === "right-full") {
      left.resize("0%");
      right.resize("100%");
    } else {
      left.resize("50%");
      right.resize("50%");
    }
    setLayout(next);
  };

  const toggleLeftMaximize = () =>
    applyLayout(layout === "left-full" ? "split" : "left-full");
  const toggleRightMaximize = () =>
    applyLayout(layout === "right-full" ? "split" : "right-full");
  const collapseLeft = () => applyLayout("right-full");
  const collapseRight = () => applyLayout("left-full");

  const goToSlug = useCallback(
    (slug: string) => {
      router.push(`/problem/${slug}`);
    },
    [router]
  );

  const handlePrev = useCallback(async () => {
    if (isNavigating) return;
    setIsNavigating(true);
    try {
      const prev = await getAdjacentProblem(problem.slug, "prev");
      if (prev) {
        goToSlug(prev.slug);
      } else {
        setHasPrev(false);
        editorHandleRef.current?.logConsole(
          "Bu ro'yxatdagi birinchi masala — oldingisi yo'q"
        );
      }
    } catch (err) {
      console.error("Oldingi masalaga o'tishda xatolik:", err);
      editorHandleRef.current?.logConsole(
        "Oldingi masalaga o'tishda xatolik yuz berdi"
      );
    } finally {
      setIsNavigating(false);
    }
  }, [isNavigating, problem.slug, goToSlug]);

  const handleNext = useCallback(async () => {
    if (isNavigating) return;
    setIsNavigating(true);
    try {
      const next = await getAdjacentProblem(problem.slug, "next");
      if (next) {
        goToSlug(next.slug);
      } else {
        setHasNext(false);
        editorHandleRef.current?.logConsole(
          "Bu ro'yxatdagi oxirgi masala — keyingisi yo'q"
        );
      }
    } catch (err) {
      console.error("Keyingi masalaga o'tishda xatolik:", err);
      editorHandleRef.current?.logConsole(
        "Keyingi masalaga o'tishda xatolik yuz berdi"
      );
    } finally {
      setIsNavigating(false);
    }
  }, [isNavigating, problem.slug, goToSlug]);

  const handleRandom = useCallback(async () => {
    if (isNavigating) return;
    setIsNavigating(true);
    try {
      const random = await getRandomProblem(problem.slug);
      goToSlug(random.slug);
    } catch (err) {
      console.error("Tasodifiy masalaga o'tishda xatolik:", err);
      editorHandleRef.current?.logConsole(
        "Tasodifiy masalaga o'tishda xatolik yuz berdi"
      );
    } finally {
      setIsNavigating(false);
    }
  }, [isNavigating, problem.slug, goToSlug]);

  const handleNavbarAction = useCallback((label: string) => {
    editorHandleRef.current?.logConsole(label);
  }, []);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] w-full flex-col bg-neutral-50 dark:bg-neutral-900">
      <ProblemNavbar
        slug={problem.slug}
        onRun={() => editorHandleRef.current?.run()}
        onSubmit={() => editorHandleRef.current?.submit()}
        isRunning={isRunning}
        isSubmitting={isSubmitting}
        onPrev={handlePrev}
        onNext={handleNext}
        onRandom={handleRandom}
        isNavigating={isNavigating}
        hasPrev={hasPrev}
        hasNext={hasNext}
        onAction={handleNavbarAction}
      />

      <div className="relative min-h-0 flex-1 p-2">
        <ResizablePanelGroup orientation={isMobile ? "vertical" : "horizontal"}>
          <ResizablePanel
            panelRef={leftPanelRef}
            defaultSize="50%"
            minSize="0%"
            onResize={(size: any) => {
              if (size > 5 && layout === "left-full") setLayout("split");
            }}
          >
            <div className="group relative h-full overflow-hidden rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
              {layout !== "right-full" && (
                <div className="absolute right-2 top-2 z-20 flex items-center gap-0.5 rounded-lg opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={toggleLeftMaximize}
                    aria-label={
                      layout === "left-full"
                        ? "Panelni tiklash"
                        : "Panelni to'liq oynaga yoyish"
                    }
                    className={toolbarButtonClass}
                  >
                    {layout === "left-full" ? (
                      <Minimize className="size-3.5" />
                    ) : (
                      <Scan className="size-3.5" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={collapseLeft}
                    aria-label="Description panelini yopish"
                    className={toolbarButtonClass}
                  >
                    <ChevronLeft className="size-3.5" />
                  </button>
                </div>
              )}
              <DescriptionPanel problem={problem} />
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle className="mx-1" />

          <ResizablePanel
            panelRef={rightPanelRef}
            defaultSize="50%"
            minSize="0%"
            onResize={(size: any) => {
              if (size > 5 && layout === "right-full") setLayout("split");
            }}
          >
            <div className="group relative h-full overflow-hidden rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
              {layout !== "left-full" && (
                <div className="absolute right-2 top-2 z-20 flex items-center gap-0.5 rounded-lg opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={collapseRight}
                    aria-label="Code editor panelini yopish"
                    className={toolbarButtonClass}
                  >
                    <ChevronRight className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={toggleRightMaximize}
                    aria-label={
                      layout === "right-full"
                        ? "Panelni tiklash"
                        : "Panelni to'liq oynaga yoyish"
                    }
                    className={toolbarButtonClass}
                  >
                    {layout === "right-full" ? (
                      <Minimize className="size-3.5" />
                    ) : (
                      <Scan className="size-3.5" />
                    )}
                  </button>
                </div>
              )}
              <CodeEditorPanel
                ref={editorHandleRef}
                problem={problem}
                onRunStateChange={setIsRunning}
                onSubmitStateChange={setIsSubmitting}
              />
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>

        {layout === "right-full" && (
          <button
            type="button"
            onClick={() => applyLayout("split")}
            aria-label="Description panelini ochish"
            className={cn(
              "absolute left-3 top-1/2 z-30 flex h-20 w-6 -translate-y-1/2 items-center justify-center",
              "rounded-r-md border border-l-0 border-neutral-200 bg-white text-neutral-400 shadow-sm",
              "transition-colors hover:bg-neutral-50 hover:text-neutral-800",
              "dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-500 dark:hover:bg-neutral-800"
            )}
          >
            <ChevronRight className="size-8" />
          </button>
        )}

        {layout === "left-full" && (
          <button
            type="button"
            onClick={() => applyLayout("split")}
            aria-label="Code editor panelini ochish"
            className={cn(
              "absolute right-3 top-1/2 z-30 flex h-20 w-6 -translate-y-1/2 items-center justify-center",
              "rounded-l-md border border-r-0 border-neutral-200 bg-white text-neutral-400 shadow-sm",
              "transition-colors hover:bg-neutral-50 hover:text-neutral-800",
              "dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-500 dark:hover:bg-neutral-800"
            )}
          >
            <ChevronLeft className="size-8" />
          </button>
        )}
      </div>

      <SubmissionTracker
        submission={submission}
        open={trackerOpen}
        onOpen={() => setTrackerOpen(true)}
        onClose={() => setTrackerOpen(false)}
      />
    </div>
  );
}