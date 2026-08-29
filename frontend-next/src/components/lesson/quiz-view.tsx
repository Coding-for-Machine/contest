import { useState, useCallback } from "react";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  Trophy,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { completeQuizClient } from "@/lib/lesson/api";
import { VideoPlayer } from "@/components/VideoPlayer";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { QuizCompleteResult, QuizDetail } from "@/lib/lesson/types";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface QuizViewProps {
  lessonSlug: string;
  questionId: number;
  quiz: QuizDetail;
  onCompleted: (xp: number) => void;
}

type ChoiceStatus = "idle" | "selected" | "correct" | "wrong";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function getChoiceStatus(
  choiceId: number,
  selectedChoice: number | null,
  result: QuizCompleteResult | null
): ChoiceStatus {
  if (!result) {
    return selectedChoice === choiceId ? "selected" : "idle";
  }
  if (result.ans.id !== choiceId) return "idle";
  return result.ans.correct ? "correct" : "wrong";
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export function QuizView({
  lessonSlug,
  questionId,
  quiz,
  onCompleted,
}: QuizViewProps) {
  const [selectedChoice, setSelectedChoice] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<QuizCompleteResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isCompleted = quiz.done || result?.ans.correct === true;

  const handleSelect = useCallback(
    (choiceId: number) => {
      if (isCompleted || result?.ans.correct) return;
      setSelectedChoice(choiceId);
    },
    [isCompleted, result?.ans.correct]
  );

  const handleSubmit = useCallback(async () => {
    if (selectedChoice === null || isSubmitting || isCompleted) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const res = await completeQuizClient(
        lessonSlug,
        questionId,
        selectedChoice
      );
      setResult(res);

      if (res.ans.correct && res.xp > 0) {
        onCompleted(res.xp);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xatolik yuz berdi");
    } finally {
      setIsSubmitting(false);
    }
  }, [lessonSlug, questionId, selectedChoice, isSubmitting, isCompleted, onCompleted]);

  const handleRetry = useCallback(() => {
    setResult(null);
    setSelectedChoice(null);
    setError(null);
  }, []);

  /* ---------- Styles ---------- */

  const choiceStatusStyles: Record<ChoiceStatus, string> = {
    idle: "border-neutral-200 hover:bg-neutral-50",
    selected: "border-amber-400 bg-amber-50 ring-2 ring-amber-200",
    correct: "border-green-500 bg-green-50 text-green-800",
    wrong: "border-red-500 bg-red-50 text-red-700",
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      {/* ===== QUESTION CARD ===== */}
      <div className="rounded-2xl border bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold uppercase text-neutral-600">
            {quiz.difficulty}
          </span>

          <div className="flex items-center gap-1.5 rounded-full bg-amber-50 px-4 py-1.5 font-bold text-amber-500">
            <Trophy className="size-4" />
            {quiz.xp} XP
          </div>
        </div>

        {/* ← BU YERDA O'ZGARDI: MarkdownRenderer orqali */}
        <div className="mt-6 text-2xl font-semibold leading-relaxed text-neutral-900">
          <MarkdownRenderer content={quiz.text} />
        </div>
      </div>

      {/* ===== CHOICES ===== */}
      <div className="mt-6 space-y-3">
        {quiz.choices.map((choice) => {
          const status = getChoiceStatus(choice.id, selectedChoice, result);

          return (
            <button
              key={choice.id}
              disabled={isCompleted}
              onClick={() => handleSelect(choice.id)}
              className={cn(
                "flex w-full items-center justify-between rounded-xl border px-5 py-4 text-left transition-all duration-200",
                choiceStatusStyles[status]
              )}
            >
              {/* ← BU YERDA O'ZGARDI: MarkdownRenderer inline orqali */}
              <span className="text-base">
                <MarkdownRenderer content={choice.text} inline />
              </span>

              {status === "correct" && (
                <CheckCircle2 className="ml-3 size-5 shrink-0 text-green-600" />
              )}
              {status === "wrong" && (
                <XCircle className="ml-3 size-5 shrink-0 text-red-600" />
              )}
            </button>
          );
        })}
      </div>

      {/* ===== SUBMIT BUTTON ===== */}
      {!isCompleted && (
        <button
          onClick={handleSubmit}
          disabled={selectedChoice === null || isSubmitting}
          className={cn(
            "mt-7 flex h-12 w-full items-center justify-center gap-2",
            "rounded-xl bg-neutral-900 font-semibold text-white",
            "hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          )}
        >
          {isSubmitting && <Loader2 className="size-5 animate-spin" />}
          Javobni tekshirish
        </button>
      )}

      {/* ===== RESULT ===== */}
      {result && (
        <div
          className={cn(
            "mt-8 rounded-2xl border p-6",
            result.ans.correct
              ? "border-green-200 bg-green-50"
              : "border-red-200 bg-red-50"
          )}
        >
          <div className="flex items-center justify-between">
            <h3
              className={cn(
                "text-lg font-bold",
                result.ans.correct ? "text-green-700" : "text-red-700"
              )}
            >
              {result.ans.correct ? "To'g'ri javob 🎉" : "Noto'g'ri javob ❌"}
            </h3>

            {result.ans.correct && result.xp > 0 && (
              <div className="flex items-center gap-1 rounded-full bg-amber-100 px-4 py-2 font-bold text-amber-600">
                <Sparkles className="size-4" />
                +{result.xp} XP
              </div>
            )}
          </div>

          {result.exp && (
            <div className="mt-5 rounded-xl bg-white p-4 text-neutral-700">
              <MarkdownRenderer content={result.exp} />
            </div>
          )}

          {result.video?.url && (
            <div className="mt-5 overflow-hidden rounded-xl">
              <VideoPlayer
                src={result.video.url}
                poster={result.video.img ?? undefined}
              />
            </div>
          )}

          {!result.ans.correct && (
            <button
              onClick={handleRetry}
              className="mt-5 rounded-lg bg-neutral-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-neutral-800"
            >
              Qayta urinish
            </button>
          )}
        </div>
      )}

      {/* ===== ERROR ===== */}
      {error && (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}
