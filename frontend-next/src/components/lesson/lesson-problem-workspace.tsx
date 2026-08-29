"use client";

import { useEffect, useRef, useState } from "react";
import { Scan, Minimize, ChevronLeft, ChevronRight } from "lucide-react";
import type { PanelImperativeHandle } from "react-resizable-panels";
import type { LessonProblemDetail } from "@/lib/lesson/types";

// NOTE: loyihangizdagi haqiqiy joylashuvga qarab moslashtiring.
import {
  CodeEditorPanel,
  type CodeEditorPanelHandle,
} from "@/components/problems/code-editor-panel";
import { SubmissionTracker } from "@/components/problems/submission-result-modal";
import { useSubmissionTracker } from "@/hooks/useSubmissionTracker";
import submissionTracker from "@/lib/submissions/tracker";

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { cn } from "@/lib/utils";

import { LessonProblemNavbar } from "./lesson-problem-navbar";
import { LessonProblemDescription } from "./lesson-problem-description";

interface LessonProblemWorkspaceProps {
  lessonSlug: string;
  problem: LessonProblemDetail;
  /** Foydalanuvchi masalani AC bilan yechganda (birinchi marta) chaqiriladi */
  onSolved?: (xp: number) => void;
  /** Sidebar'dagi boshqa bo'limga qaytish (masalan darsning umumiy holatiga) */
  onBack?: () => void;
}

type Layout = "split" | "left-full" | "right-full";

const toolbarButtonClass = cn(
  "flex h-7 w-7 items-center justify-center rounded-md text-neutral-400",
  "bg-transparent transition-colors",
  "hover:bg-neutral-100 hover:text-neutral-800"
);

export function LessonProblemWorkspace({
  lessonSlug,
  problem,
  onSolved,
  onBack,
}: LessonProblemWorkspaceProps) {
  const [isMobile, setIsMobile] = useState(false);
  const [layout, setLayout] = useState<Layout>("split");

  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const leftPanelRef = useRef<PanelImperativeHandle>(null);
  const rightPanelRef = useRef<PanelImperativeHandle>(null);
  const editorHandleRef = useRef<CodeEditorPanelHandle>(null);

  // === SUBMISSION TRACKER / MODAL ===
  const submission = useSubmissionTracker();
  const [trackerOpen, setTrackerOpen] = useState(false);
  const lastSubmissionId = useRef<string | null>(null);
  const notifiedSolvedRef = useRef(false);

  useEffect(() => {
    lastSubmissionId.current = submission?.id ?? null;
    notifiedSolvedRef.current = problem.solved;
  }, [problem.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (submission?.id && submission.id !== lastSubmissionId.current) {
      lastSubmissionId.current = submission.id;
      setTrackerOpen(true);
    }
  }, [submission?.id]);

  // Muvaffaqiyatli (AC) submission bo'lganda darsga bir marta xabar beramiz
  useEffect(() => {
    const final = submission?.final;
    if (!final || notifiedSolvedRef.current) return;

    if (final.total_count > 0 && final.passed_count === final.total_count) {
      notifiedSolvedRef.current = true;
      onSolved?.(problem.xp);
    }
  }, [submission?.final, onSolved, problem.xp]);

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

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white">
      <LessonProblemNavbar
        lessonSlug={lessonSlug}
        problemTitle={problem.title}
        solved={problem.solved}
        onRun={() => editorHandleRef.current?.run()}
        onSubmit={() => editorHandleRef.current?.submit()}
        isRunning={isRunning}
        isSubmitting={isSubmitting}
        onBack={onBack}
      />

      <div className="relative min-h-0 flex-1 p-2">
        <ResizablePanelGroup
          orientation={isMobile ? "vertical" : "horizontal"}
        >
          <ResizablePanel
            panelRef={leftPanelRef}
            defaultSize="50%"
            minSize="0%"
            onResize={(size: any) => {
              if (size > 5 && layout === "left-full") setLayout("split");
            }}
          >
            <div className="group relative h-full overflow-hidden rounded-xl border border-neutral-200 bg-white">
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
                    aria-label="Tavsif panelini yopish"
                    className={toolbarButtonClass}
                  >
                    <ChevronLeft className="size-3.5" />
                  </button>
                </div>
              )}
              <LessonProblemDescription problem={problem} />
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
            <div className="group relative h-full overflow-hidden rounded-xl border border-neutral-200 bg-white">
              {layout !== "left-full" && (
                <div className="absolute right-2 top-2 z-20 flex items-center gap-0.5 rounded-lg opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={collapseRight}
                    aria-label="Kod muharriri panelini yopish"
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
                problem={problem as any}
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
            aria-label="Tavsif panelini ochish"
            className={cn(
              "absolute left-3 top-1/2 z-30 flex h-20 w-6 -translate-y-1/2 items-center justify-center",
              "rounded-r-md border border-l-0 border-neutral-200 bg-white text-neutral-400 shadow-sm",
              "transition-colors hover:bg-neutral-50 hover:text-neutral-800"
            )}
          >
            <ChevronRight className="size-8" />
          </button>
        )}

        {layout === "left-full" && (
          <button
            type="button"
            onClick={() => applyLayout("split")}
            aria-label="Kod muharriri panelini ochish"
            className={cn(
              "absolute right-3 top-1/2 z-30 flex h-20 w-6 -translate-y-1/2 items-center justify-center",
              "rounded-l-md border border-r-0 border-neutral-200 bg-white text-neutral-400 shadow-sm",
              "transition-colors hover:bg-neutral-50 hover:text-neutral-800"
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