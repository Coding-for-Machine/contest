"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, XCircle, Loader2, PlayCircle, Award, RotateCcw } from "lucide-react";
import { getQuizDetail, submitQuizAnswer } from "@/lib/api/courses";
import type { QuizDetail, QuizAnswerResult } from "@/lib/types/course";

interface QuizViewProps {
  lessonSlug: string;
  questionId: number;
  initialData?: QuizDetail | null;
}

export function QuizView({ lessonSlug, questionId, initialData }: QuizViewProps) {
  const router = useRouter();
  const [quiz, setQuiz] = useState<QuizDetail | null>(initialData ?? null);
  const [result, setResult] = useState<QuizAnswerResult | null>(null);
  const [selectedChoice, setSelectedChoice] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(!initialData);

  // Agar initialData bo'lmasa, client-side yuklash
  const loadQuiz = useCallback(async () => {
    setIsLoading(true);
    const data = await getQuizDetail(lessonSlug, questionId);
    setQuiz(data);
    setIsLoading(false);
  }, [lessonSlug, questionId]);

  const handleSubmit = async () => {
    if (!selectedChoice || !quiz) return;

    setIsSubmitting(true);
    const res = await submitQuizAnswer(lessonSlug, questionId, selectedChoice);
    setIsSubmitting(false);

    if (res) {
      setResult(res);
      // XP animatsiyasi yoki refresh
      if (res.answer.correct) {
        router.refresh();
      }
    }
  };

  const handleRetry = () => {
    setResult(null);
    setSelectedChoice(null);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-[#D9AE55]" />
      </div>
    );
  }

  if (!quiz) {
    return (
      <div className="rounded-xl border border-white/10 bg-[#121212] p-8 text-center text-white/50">
        Savol topilmadi
      </div>
    );
  }

  // Agar allaqachon to'g'ri javob bergan bo'lsa
  if (quiz.done && !result) {
    return (
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-8 text-center">
        <CheckCircle2 className="mx-auto size-12 text-emerald-500" />
        <h3 className="mt-4 text-lg font-semibold text-emerald-400">
          Allaqachon bajarilgan
        </h3>
        <p className="mt-1 text-sm text-white/50">
          Bu savolga to'g'ri javob bergansiz. +{quiz.xp} XP
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-[#121212] p-6 sm:p-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Award className="size-5 text-[#D9AE55]" />
          <span className="text-sm font-medium text-white/70">
            Savol #{questionId}
          </span>
        </div>
        <span className="rounded-full bg-[#D9AE55]/10 px-3 py-1 text-xs font-medium text-[#D9AE55]">
          {quiz.xp} XP
        </span>
      </div>

      {/* Question */}
      <h2 className="mb-6 text-lg font-semibold leading-relaxed text-white">
        {quiz.text}
      </h2>

      {/* Result state */}
      {result ? (
        <div className="space-y-4">
          <div
            className={`flex items-center gap-3 rounded-lg border p-4 ${
              result.answer.correct
                ? "border-emerald-500/30 bg-emerald-500/10"
                : "border-red-500/30 bg-red-500/10"
            }`}
          >
            {result.answer.correct ? (
              <CheckCircle2 className="size-6 text-emerald-500" />
            ) : (
              <XCircle className="size-6 text-red-400" />
            )}
            <div>
              <p
                className={`font-medium ${
                  result.answer.correct ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {result.answer.correct ? "To'g'ri javob!" : "Noto'g'ri javob"}
              </p>
              {!result.answer.correct && (
                <p className="text-sm text-white/50">Qayta urinib ko'ring</p>
              )}
            </div>
          </div>

          {result.explanation && (
            <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
              <p className="text-sm leading-relaxed text-white/70">
                {result.explanation}
              </p>
            </div>
          )}

          {result.video?.url && (
            <div className="aspect-video overflow-hidden rounded-lg border border-white/10 bg-black">
              <video
                src={result.video.url}
                poster={result.video.thumbnail}
                controls
                className="h-full w-full"
              />
            </div>
          )}

          <div className="flex gap-3 pt-2">
            {!result.answer.correct && (
              <button
                onClick={handleRetry}
                className="flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/5"
              >
                <RotateCcw className="size-4" />
                Qayta urinish
              </button>
            )}
            <button
              onClick={() => router.refresh()}
              className="rounded-lg bg-[#D9AE55] px-4 py-2.5 text-sm font-medium text-black transition hover:opacity-90"
            >
              Davom etish
            </button>
          </div>
        </div>
      ) : (
        /* Choices */
        <div className="space-y-2">
          {quiz.choices.map((choice) => {
            const isSelected = selectedChoice === choice.id;
            return (
              <button
                key={choice.id}
                onClick={() => setSelectedChoice(choice.id)}
                className={`flex w-full items-center gap-3 rounded-lg border p-4 text-left transition ${
                  isSelected
                    ? "border-[#D9AE55]/50 bg-[#D9AE55]/10"
                    : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                }`}
              >
                <div
                  className={`flex size-5 shrink-0 items-center justify-center rounded-full border ${
                    isSelected
                      ? "border-[#D9AE55] bg-[#D9AE55]"
                      : "border-white/30"
                  }`}
                >
                  {isSelected && <div className="size-2 rounded-full bg-black" />}
                </div>
                <span className="text-sm text-white/80">{choice.text}</span>
              </button>
            );
          })}

          <button
            onClick={handleSubmit}
            disabled={!selectedChoice || isSubmitting}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#D9AE55] px-4 py-3 text-sm font-medium text-black transition hover:opacity-90 disabled:opacity-40"
          >
            {isSubmitting ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              "Javobni yuborish"
            )}
          </button>
        </div>
      )}
    </div>
  );
}