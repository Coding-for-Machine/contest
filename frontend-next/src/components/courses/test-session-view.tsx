"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Play,
  Clock,
  Award,
  HelpCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  RotateCcw,
  ArrowRight,
} from "lucide-react";
import { startTestSession, submitTestAnswer, finishTestSession } from "@/lib/api/courses";
import type { TestInfo, TestQuestion, TestFinishResponse } from "@/lib/types/course-test";

interface TestSessionViewProps {
  modulId: number;
  courseSlug: string;
  testInfo: TestInfo;
}

type Stage = "intro" | "loading" | "in_progress" | "finishing" | "result";

function formatClock(totalSeconds: number) {
  const safe = Math.max(0, totalSeconds);
  const m = Math.floor(safe / 60);
  const s = safe % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function TestSessionView({ modulId, courseSlug, testInfo }: TestSessionViewProps) {
  const [stage, setStage] = useState<Stage>("intro");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<TestQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number | null>>({});
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [finishResult, setFinishResult] = useState<TestFinishResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentQuestion = questions[currentIndex];
  const isLastQuestion = currentIndex === questions.length - 1;
  const selectedChoice = currentQuestion ? answers[currentQuestion.id] ?? null : null;

  const persistCurrentAnswer = async (activeSessionId: string) => {
    if (!currentQuestion) return;
    const choiceId = answers[currentQuestion.id] ?? null;
    await submitTestAnswer(activeSessionId, currentQuestion.id, choiceId);
  };

  const handleFinish = async () => {
    if (!sessionId) return;
    setStage("finishing");
    await persistCurrentAnswer(sessionId);

    const res = await finishTestSession(sessionId);
    if (!res) {
      setError("Natijani hisoblashda xatolik yuz berdi");
      setStage("in_progress");
      return;
    }
    setFinishResult(res);
    setStage("result");
  };

  // Timer — har soniyada kamayadi, 0 ga yetganda avtomatik yakunlaydi
  useEffect(() => {
    if (stage !== "in_progress") return;
    if (secondsLeft <= 0) {
      handleFinish();
      return;
    }
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, secondsLeft]);

  const handleStart = async () => {
    setStage("loading");
    setError(null);

    const res = await startTestSession(modulId);
    if (!res) {
      setError("Testni boshlashda xatolik yuz berdi");
      setStage("intro");
      return;
    }

    setSessionId(res.session_id);
    setQuestions(res.questions);
    setSecondsLeft(res.duration_minutes * 60);
    setCurrentIndex(0);
    setAnswers({});
    setFinishResult(null);
    setStage("in_progress");
  };

  const selectChoice = (choiceId: number) => {
    if (!currentQuestion) return;
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: choiceId }));
  };

  const handleNext = async () => {
    if (!sessionId) return;
    await persistCurrentAnswer(sessionId);

    if (isLastQuestion) {
      await handleFinish();
      return;
    }
    setCurrentIndex((i) => i + 1);
  };

  const scorePct = useMemo(() => {
    if (!finishResult) return 0;
    const total = finishResult.correct + finishResult.wrong + finishResult.unanswered;
    return total > 0 ? Math.round((finishResult.correct / total) * 100) : 0;
  }, [finishResult]);

  const passed = finishResult ? scorePct >= testInfo.min_pass_percentage : false;

  /* ==================== INTRO ==================== */
  if (stage === "intro" || stage === "loading") {
    return (
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#121212]">
        {testInfo.video?.thumbnail && (
          <div className="relative aspect-video">
            <Image src={testInfo.video.thumbnail} alt={testInfo.title} fill className="object-cover" />
            <div className="absolute inset-0 bg-black/40" />
          </div>
        )}

        <div className="p-8">
          <h1 className="font-display text-2xl font-bold text-white">{testInfo.title}</h1>
          {testInfo.description && (
            <p className="mt-3 text-sm leading-relaxed text-white/50">{testInfo.description}</p>
          )}

          <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-white/40">
            <span className="flex items-center gap-2">
              <Clock className="size-4 text-[#D9AE55]" />
              {testInfo.duration_minutes} daqiqa
            </span>
            <span className="flex items-center gap-2">
              <HelpCircle className="size-4 text-[#D9AE55]" />
              {testInfo.question_count} savol
            </span>
            <span className="flex items-center gap-2">
              <Award className="size-4 text-[#D9AE55]" />
              O'tish balli: {testInfo.min_pass_percentage}%
            </span>
          </div>

          {testInfo.best_result && (
            <div className="mt-6 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
              <p className="text-sm font-medium text-emerald-400">
                Eng yaxshi natijangiz: {testInfo.best_result.correct} to'g'ri · {testInfo.best_result.xp} XP
              </p>
            </div>
          )}

          {error && (
            <div className="mt-6 rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            onClick={handleStart}
            disabled={stage === "loading"}
            className="mt-8 flex w-full items-center justify-center gap-2 rounded-lg bg-[#D9AE55] px-6 py-3 text-sm font-semibold text-[#121212] transition hover:opacity-90 disabled:opacity-50 sm:w-auto"
          >
            {stage === "loading" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : testInfo.active_session_id ? (
              <>
                Davom ettirish
                <Play className="size-4" />
              </>
            ) : (
              <>
                Testni boshlash
                <Play className="size-4" />
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  /* ==================== IN PROGRESS ==================== */
  if (stage === "in_progress" && currentQuestion) {
    return (
      <div className="rounded-2xl border border-white/10 bg-[#121212] p-6 sm:p-8">
        <div className="mb-6 flex items-center justify-between">
          <span className="text-xs font-mono text-white/40">
            Savol {currentIndex + 1} / {questions.length}
          </span>
          <span className="flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs font-medium text-[#D9AE55]">
            <Clock className="size-3.5" />
            {formatClock(secondsLeft)}
          </span>
        </div>

        <div className="mb-6 h-1 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-[#D9AE55] transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          />
        </div>

        <h2 className="mb-6 text-lg font-semibold leading-relaxed text-white">
          {currentQuestion.text}
        </h2>

        <div className="space-y-2">
          {currentQuestion.choices.map((choice) => {
            const isSelected = selectedChoice === choice.id;
            return (
              <button
                key={choice.id}
                onClick={() => selectChoice(choice.id)}
                className={`flex w-full items-center gap-3 rounded-lg border p-4 text-left transition ${
                  isSelected
                    ? "border-[#D9AE55]/50 bg-[#D9AE55]/10"
                    : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                }`}
              >
                <div
                  className={`flex size-5 shrink-0 items-center justify-center rounded-full border ${
                    isSelected ? "border-[#D9AE55] bg-[#D9AE55]" : "border-white/30"
                  }`}
                >
                  {isSelected && <div className="size-2 rounded-full bg-black" />}
                </div>
                <span className="text-sm text-white/80">{choice.text}</span>
              </button>
            );
          })}
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <button
            onClick={handleNext}
            className="flex items-center gap-2 rounded-lg bg-[#D9AE55] px-6 py-2.5 text-sm font-medium text-black transition hover:opacity-90"
          >
            {isLastQuestion ? "Testni yakunlash" : "Keyingisi"}
            <ArrowRight className="size-4" />
          </button>
        </div>
      </div>
    );
  }

  /* ==================== FINISHING ==================== */
  if (stage === "finishing") {
    return (
      <div className="flex min-h-[300px] items-center justify-center rounded-2xl border border-white/10 bg-[#121212]">
        <Loader2 className="size-8 animate-spin text-[#D9AE55]" />
      </div>
    );
  }

  /* ==================== RESULT ==================== */
  if (stage === "result" && finishResult) {
    return (
      <div className="rounded-2xl border border-white/10 bg-[#121212] p-8 text-center">
        {passed ? (
          <CheckCircle2 className="mx-auto size-14 text-emerald-500" />
        ) : (
          <XCircle className="mx-auto size-14 text-red-400" />
        )}

        <h2 className={`mt-4 text-2xl font-bold ${passed ? "text-emerald-400" : "text-red-400"}`}>
          {passed ? "Tabriklaymiz, o'tdingiz!" : "Afsuski, o'ta olmadingiz"}
        </h2>

        <p className="mt-2 text-sm text-white/50">
          {scorePct}% to'g'ri javob · o'tish balli {testInfo.min_pass_percentage}%
        </p>

        <div className="mx-auto mt-8 grid max-w-sm grid-cols-3 gap-3 text-center">
          <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
            <div className="text-xl font-bold text-emerald-400">{finishResult.correct}</div>
            <div className="mt-1 text-xs text-white/40">To'g'ri</div>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
            <div className="text-xl font-bold text-red-400">{finishResult.wrong}</div>
            <div className="mt-1 text-xs text-white/40">Noto'g'ri</div>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
            <div className="text-xl font-bold text-white/50">{finishResult.unanswered}</div>
            <div className="mt-1 text-xs text-white/40">Javobsiz</div>
          </div>
        </div>

        <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#D9AE55]/10 px-4 py-1.5 text-sm font-medium text-[#D9AE55]">
          <Award className="size-4" />
          +{finishResult.xp} XP
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          {!passed && (
            <button
              onClick={handleStart}
              className="flex items-center gap-2 rounded-lg border border-white/15 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-white/5"
            >
              <RotateCcw className="size-4" />
              Qayta urinish
            </button>
          )}
          <Link
            href={`/courses/${courseSlug}`}
            className="flex items-center gap-2 rounded-lg bg-[#D9AE55] px-6 py-2.5 text-sm font-medium text-black transition hover:opacity-90"
          >
            Kursga qaytish
            <ArrowRight className="size-4" />
          </Link>
        </div>
      </div>
    );
  }

  return null;
}