"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/utils";
import { apiPost } from "@/lib/tests/api";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import type {
  SessionQuestionsResponse,
  SessionStatusResponse,
  FinishResponse,
  LifelineResponse,
  ApiError,
  SessionQuestion,
  SessionChoice,
} from "@/lib/tests/types";
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  Heart,
  CheckCircle2,
  Circle,
  AlertCircle,
  Loader2,
  Send,
  X,
  Menu,
  Flag,
  RotateCcw,
  Zap,
  PanelLeftClose,
  PanelLeft,
  Bookmark,
  Keyboard,
} from "lucide-react";

/* ================================================================
   HELPERS
   ================================================================ */
function formatTime(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function getInitials(name: string) {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

/* ================================================================
   MAIN EXAM PAGE
   ================================================================ */
export default function ExamPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");

  /* ---------- Local session cache from sessionStorage ---------- */
  const [session, setSession] = useState<{
    session_id: string;
    title: string;
    questions: SessionQuestion[];
    duration_minutes: number;
    expires_at: string;
    lifelines: number;
  } | null>(null);

  const [mounted, setMounted] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [answers, setAnswers] = useState<Record<number, number | null>>({});
  const [eliminated, setEliminated] = useState<Record<number, number[]>>({});
  const [marked, setMarked] = useState<Set<number>>(new Set());
  const [timeLeft, setTimeLeft] = useState(0);
  const [lifelinesLeft, setLifelinesLeft] = useState(0);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [finishOpen, setFinishOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [syncStatus, setSyncStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [lifelineLoading, setLifelineLoading] = useState(false);

  const saveTimer = useRef<NodeJS.Timeout | null>(null);
  const mainRef = useRef<HTMLDivElement>(null);

  /* ---------- Load session from storage ---------- */
  useEffect(() => {
    setMounted(true);
    const raw = sessionStorage.getItem("quiz_active_session");
    if (!raw || !sessionId) {
      router.replace("/tests");
      return;
    }
    try {
      const data = JSON.parse(raw);
      if (data.session_id !== sessionId) {
        router.replace("/tests");
        return;
      }
      setSession(data);
      setLifelinesLeft(data.lifelines || 0);
      const exp = new Date(data.expires_at).getTime();
      const left = Math.max(0, Math.floor((exp - Date.now()) / 1000));
      setTimeLeft(left);

      // Pre-fill saved answers if any (from previous partial attempt)
      if (data.saved_answers) {
        const saved: Record<number, number | null> = {};
        Object.entries(data.saved_answers).forEach(([k, v]) => {
          saved[Number(k)] = v as number | null;
        });
        setAnswers(saved);
      }
    } catch {
      router.replace("/tests");
    }
  }, [sessionId, router]);

  /* ---------- Fetch live session status ---------- */
  const { data: liveStatus } = useSWR<SessionStatusResponse>(
    sessionId ? `/api/test-session/session/${sessionId}` : null,
    fetcher,
    { refreshInterval: 30_000, revalidateOnFocus: true }
  );

  useEffect(() => {
    if (liveStatus) {
      setTimeLeft(liveStatus.remaining_seconds);
    }
  }, [liveStatus]);

  /* ---------- Countdown timer ---------- */
  useEffect(() => {
    if (timeLeft <= 0) return;
    const id = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(id);
          handleFinish(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft]);

  /* ---------- Before unload warning ---------- */
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!submitting && timeLeft > 0) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [submitting, timeLeft]);

  /* ---------- Keyboard shortcuts ---------- */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore if typing in input or modal open
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        finishOpen
      )
        return;

      const q = session?.questions[currentIdx];
      if (!q) return;

      // Number keys 1-9: select choice
      if (e.key >= "1" && e.key <= "9") {
        const idx = parseInt(e.key, 10) - 1;
        const choice = q.choices[idx];
        if (choice && !isEliminated(q.id, choice.id)) {
          selectAnswer(q.id, choice.id);
        }
        return;
      }

      switch (e.key) {
        case "ArrowRight":
          e.preventDefault();
          goNext();
          break;
        case "ArrowLeft":
          e.preventDefault();
          goPrev();
          break;
        case "ArrowUp":
          e.preventDefault();
          if (currentIdx > 0) goTo(currentIdx - 1, -1);
          break;
        case "ArrowDown":
          e.preventDefault();
          if (currentIdx < (session?.questions.length || 0) - 1) goTo(currentIdx + 1, 1);
          break;
        case "m":
        case "M":
          toggleMark(currentIdx);
          break;
        case "l":
        case "L":
          e.preventDefault();
          useLifeline();
          break;
        case "Enter":
          if (e.ctrlKey) {
            e.preventDefault();
            setFinishOpen(true);
          }
          break;
        case "?":
          e.preventDefault();
          setShowShortcuts((v) => !v);
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIdx, session, finishOpen, eliminated, answers, lifelinesLeft]);

  /* ---------- Navigation ---------- */
  const goTo = useCallback(
    (idx: number, dir: 1 | -1) => {
      if (!session) return;
      if (idx < 0 || idx >= session.questions.length) return;
      setDirection(dir);
      setCurrentIdx(idx);
      // Scroll to top of question
      mainRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    },
    [session]
  );

  const goNext = useCallback(() => {
    if (!session) return;
    if (currentIdx < session.questions.length - 1) goTo(currentIdx + 1, 1);
  }, [currentIdx, session, goTo]);

  const goPrev = useCallback(() => {
    if (currentIdx > 0) goTo(currentIdx - 1, -1);
  }, [currentIdx, goTo]);

  /* ---------- Answer selection ---------- */
  const selectAnswer = useCallback(
    (questionId: number, choiceId: number | null) => {
      setAnswers((prev) => ({ ...prev, [questionId]: choiceId }));
      setSyncStatus("saving");
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(async () => {
        try {
          await apiPost(`/test-session/session/${sessionId}/answer`, {
            question_id: questionId,
            choice_id: choiceId,
          });
          setSyncStatus("saved");
          setTimeout(() => setSyncStatus("idle"), 1200);
        } catch {
          setSyncStatus("error");
        }
      }, 500);
    },
    [sessionId]
  );

  /* ---------- Mark for review ---------- */
  const toggleMark = useCallback((idx: number) => {
    setMarked((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  /* ---------- Lifeline (50/50) ---------- */
  const useLifeline = useCallback(async () => {
    if (!session || lifelinesLeft <= 0 || lifelineLoading) return;
    const q = session.questions[currentIdx];
    if (!q) return;
    // Already answered or already used on this question?
    if (answers[q.id] !== undefined && answers[q.id] !== null) return;
    if ((eliminated[q.id]?.length || 0) > 0) return;

    setLifelineLoading(true);
    try {
      const res = await apiPost<LifelineResponse>(
        `/test-session/session/${sessionId}/lifeline`,
        { question_id: q.id }
      );
      setEliminated((prev) => ({
        ...prev,
        [q.id]: res.eliminated_choice_ids,
      }));
      setLifelinesLeft(res.lifelines_left);
    } catch {
      // fail silently or show toast
    } finally {
      setLifelineLoading(false);
    }
  }, [session, currentIdx, lifelinesLeft, lifelineLoading, answers, eliminated, sessionId]);

  function isEliminated(questionId: number, choiceId: number) {
    return eliminated[questionId]?.includes(choiceId) ?? false;
  }

  /* ---------- Finish / Submit ---------- */
  const handleFinish = useCallback(
    async (auto = false) => {
      if (!sessionId || submitting) return;
      setSubmitting(true);
      try {
        // Bulk save all answers first
        const payload = Object.entries(answers).map(([qid, cid]) => ({
          question_id: Number(qid),
          choice_id: cid,
        }));
        await apiPost(`/test-session/session/${sessionId}/answers/bulk`, {
          answers: payload,
        });

        const res = await apiPost<FinishResponse>(
          `/test-session/session/${sessionId}/finish`,
          {}
        );

        sessionStorage.removeItem("quiz_active_session");
        router.push(`/tests/review/${sessionId}`);
      } catch (e) {
        const err = e as ApiError;
        if (!auto) alert(err.message || "Yuborishda xatolik yuz berdi.");
      } finally {
        setSubmitting(false);
        setFinishOpen(false);
      }
    },
    [sessionId, answers, submitting, router]
  );

  /* ---------- Derived state ---------- */
  const totalQuestions = session?.questions.length || 0;
  const answeredCount = Object.values(answers).filter((v) => v !== null && v !== undefined).length;
  const currentQuestion = session?.questions[currentIdx];
  const isLast = currentIdx === totalQuestions - 1;
  const isFirst = currentIdx === 0;
  const timerWarning = timeLeft < 60;
  const timerDanger = timeLeft < 10;

  if (!mounted || !session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="text-center">
          <Loader2 className="mx-auto mb-4 size-10 animate-spin text-slate-400" />
          <p className="text-sm font-medium text-slate-500">Test yuklanmoqda...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 pb-24 lg:pb-8">
      {/* ==================== STICKY HEADER ==================== */}
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 lg:px-6">
          {/* Left: Back + Title */}
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setFinishOpen(true)}
              className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
              title="Testni yakunlash"
            >
              <ChevronLeft className="size-5" />
            </button>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-bold text-slate-900 sm:text-base">
                {session.title}
              </h1>
              <p className="hidden text-xs text-slate-500 sm:block">
                Savol {currentIdx + 1} / {totalQuestions}
              </p>
            </div>
          </div>

          {/* Center: Timer */}
          <div
            className={`flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-bold font-mono transition-colors ${
              timerDanger
                ? "animate-pulse border-red-200 bg-red-50 text-red-600"
                : timerWarning
                ? "border-amber-200 bg-amber-50 text-amber-700"
                : "border-slate-200 bg-slate-50 text-slate-700"
            }`}
          >
            <Clock className="size-4" />
            {formatTime(timeLeft)}
          </div>

          {/* Right: Palette toggle (mobile) + Lifeline */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPaletteOpen(true)}
              className="flex size-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 lg:hidden"
            >
              <Menu className="size-5" />
            </button>

            <button
              onClick={useLifeline}
              disabled={lifelinesLeft <= 0 || lifelineLoading}
              className={`hidden sm:flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                lifelinesLeft > 0
                  ? "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
                  : "border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed"
              }`}
              title="Lifeline (50/50) — L tugmasi"
            >
              {lifelineLoading ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Heart className="size-3.5" fill="currentColor" />
              )}
              {lifelinesLeft}
            </button>

            <button
              onClick={() => setShowShortcuts(true)}
              className="hidden size-9 items-center justify-center rounded-lg border border-slate-200 text-slate-400 transition hover:bg-slate-50 hover:text-slate-600 lg:flex"
              title="Klaviatura yorliqlari"
            >
              <Keyboard className="size-4" />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-1 w-full bg-slate-100">
          <div
            className="h-full bg-slate-900 transition-all duration-500"
            style={{ width: `${((currentIdx + 1) / totalQuestions) * 100}%` }}
          />
        </div>
      </header>

      {/* ==================== MAIN CONTENT ==================== */}
      <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* ---------- LEFT: Question Area ---------- */}
          <div className="lg:col-span-8">
            <div
              ref={mainRef}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              {/* Question Header */}
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                <div className="flex items-center gap-2">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white">
                    {currentIdx + 1}
                  </span>
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                    Savol
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleMark(currentIdx)}
                    className={`flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium transition ${
                      marked.has(currentIdx)
                        ? "border-amber-200 bg-amber-50 text-amber-700"
                        : "border-slate-200 text-slate-500 hover:bg-slate-50"
                    }`}
                    title="Belgilash (M)"
                  >
                    <Flag className="size-3.5" fill={marked.has(currentIdx) ? "currentColor" : "none"} />
                    {marked.has(currentIdx) ? "Belgilangan" : "Belgilash"}
                  </button>
                </div>
              </div>

              {/* Question Body */}
              <div className="px-5 py-6 sm:px-8 sm:py-8">
                {currentQuestion && (
                  <div
                    className="transition-all duration-300"
                    style={{
                      opacity: 1,
                      transform: `translateX(0)`,
                    }}
                  >
                    <div className="mb-8">
                      <MarkdownRenderer content={currentQuestion.text} />
                    </div>

                    {/* Choices */}
                    <div className="space-y-3">
                      {currentQuestion.choices.map((choice, cIdx) => {
                        const isSelected = answers[currentQuestion.id] === choice.id;
                        const isDisabled = isEliminated(currentQuestion.id, choice.id);
                        const letter = String.fromCharCode(65 + cIdx);

                        return (
                          <button
                            key={choice.id}
                            disabled={isDisabled}
                            onClick={() => selectAnswer(currentQuestion.id, choice.id)}
                            className={`group flex w-full items-start gap-4 rounded-xl border-2 px-4 py-4 text-left transition-all sm:px-5 sm:py-5 ${
                              isDisabled
                                ? "cursor-not-allowed border-slate-100 bg-slate-50 opacity-40"
                                : isSelected
                                ? "border-slate-900 bg-slate-900 text-white shadow-md"
                                : "border-slate-200 bg-white text-slate-800 hover:border-slate-400 hover:bg-slate-50"
                            }`}
                          >
                            <span
                              className={`flex size-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold transition ${
                                isDisabled
                                  ? "bg-slate-200 text-slate-400"
                                  : isSelected
                                  ? "bg-white text-slate-900"
                                  : "bg-slate-100 text-slate-600 group-hover:bg-slate-200"
                              }`}
                            >
                              {letter}
                            </span>
                            <span className="flex-1 pt-0.5 text-[15px] leading-relaxed">
                              <MarkdownRenderer
                                content={choice.text}
                                className={isSelected ? "text-white [&_strong]:text-white [&_code]:bg-white/20 [&_code]:text-white" : ""}
                              />
                            </span>
                            {isSelected && (
                              <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-white" />
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {/* Clear answer */}
                    {answers[currentQuestion.id] !== undefined && answers[currentQuestion.id] !== null && (
                      <button
                        onClick={() => selectAnswer(currentQuestion.id, null)}
                        className="mt-4 text-xs font-medium text-slate-400 underline underline-offset-2 transition hover:text-slate-600"
                      >
                        Javobni bekor qilish
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Footer: Prev / Next */}
              <div className="flex items-center justify-between border-t border-slate-100 px-5 py-4 sm:px-8">
                <button
                  onClick={goPrev}
                  disabled={isFirst}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="size-4" /> Oldingi
                </button>

                <div className="hidden text-xs text-slate-400 sm:block">
                  {syncStatus === "saving" && (
                    <span className="flex items-center gap-1">
                      <Loader2 className="size-3 animate-spin" /> Saqlanmoqda...
                    </span>
                  )}
                  {syncStatus === "saved" && (
                    <span className="flex items-center gap-1 text-emerald-600">
                      <CheckCircle2 className="size-3" /> Saqlandi
                    </span>
                  )}
                  {syncStatus === "error" && (
                    <span className="flex items-center gap-1 text-red-500">
                      <AlertCircle className="size-3" /> Saqlashda xatolik
                    </span>
                  )}
                </div>

                {isLast ? (
                  <button
                    onClick={() => setFinishOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700"
                  >
                    <Send className="size-4" /> Yakunlash
                  </button>
                ) : (
                  <button
                    onClick={goNext}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
                  >
                    Keyingi <ChevronRight className="size-4" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* ---------- RIGHT: Sidebar (Desktop) ---------- */}
          <div className="hidden lg:col-span-4 lg:block">
            <div className="sticky top-24 space-y-4">
              {/* Stats Card */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="mb-4 text-sm font-bold text-slate-900">Umumiy ma'lumot</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-center">
                    <div className="text-xl font-bold text-slate-900">{totalQuestions}</div>
                    <div className="text-xs text-slate-500">Jami savol</div>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-center">
                    <div className="text-xl font-bold text-emerald-600">{answeredCount}</div>
                    <div className="text-xs text-slate-500">Javob berilgan</div>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-center">
                    <div className="text-xl font-bold text-amber-600">{marked.size}</div>
                    <div className="text-xs text-slate-500">Belgilangan</div>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-center">
                    <div className="text-xl font-bold text-rose-600">{lifelinesLeft}</div>
                    <div className="text-xs text-slate-500">Lifeline</div>
                  </div>
                </div>

                <button
                  onClick={() => setFinishOpen(true)}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-3 text-sm font-bold text-white transition hover:bg-slate-800"
                >
                  <Send className="size-4" /> Testni yakunlash
                </button>
              </div>

              {/* Question Palette */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="mb-4 text-sm font-bold text-slate-900">Savollar ro'yxati</h3>
                <div className="grid grid-cols-5 gap-2">
                  {session.questions.map((q, idx) => {
                    const isAnswered = answers[q.id] !== null && answers[q.id] !== undefined;
                    const isCurrent = idx === currentIdx;
                    const isMarked = marked.has(idx);
                    return (
                      <button
                        key={q.id}
                        onClick={() => goTo(idx, idx > currentIdx ? 1 : -1)}
                        className={`relative flex aspect-square items-center justify-center rounded-lg text-sm font-bold transition ${
                          isCurrent
                            ? "bg-slate-900 text-white shadow-md ring-2 ring-slate-900 ring-offset-2"
                            : isAnswered
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                            : "bg-slate-50 text-slate-600 border border-slate-200 hover:border-slate-400 hover:bg-slate-100"
                        }`}
                      >
                        {idx + 1}
                        {isMarked && (
                          <span className="absolute -right-1 -top-1 flex size-3 items-center justify-center rounded-full bg-amber-400 ring-2 ring-white">
                            <span className="sr-only">Belgilangan</span>
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Legend */}
                <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <span className="size-3 rounded bg-emerald-50 border border-emerald-200" /> Javob berilgan
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-3 rounded bg-slate-900" /> Joriy
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-3 rounded bg-slate-50 border border-slate-200" /> Javobsiz
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== MOBILE BOTTOM NAV ==================== */}
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-200 bg-white/90 backdrop-blur-md lg:hidden">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <button
            onClick={goPrev}
            disabled={isFirst}
            className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:opacity-40"
          >
            <ChevronLeft className="size-5" />
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setPaletteOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
            >
              <Menu className="size-4" />
              {answeredCount}/{totalQuestions}
            </button>

            <button
              onClick={useLifeline}
              disabled={lifelinesLeft <= 0 || lifelineLoading}
              className={`flex items-center gap-1 rounded-full border px-3 py-2 text-xs font-bold transition ${
                lifelinesLeft > 0
                  ? "border-rose-200 bg-rose-50 text-rose-700"
                  : "border-slate-200 bg-slate-50 text-slate-400"
              }`}
            >
              <Heart className="size-3.5" fill="currentColor" />
              {lifelinesLeft}
            </button>
          </div>

          {isLast ? (
            <button
              onClick={() => setFinishOpen(true)}
              className="flex items-center gap-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm"
            >
              <Send className="size-4" /> Yakunlash
            </button>
          ) : (
            <button
              onClick={goNext}
              className="flex items-center gap-1 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
            >
              <ChevronRight className="size-5" />
            </button>
          )}
        </div>
      </div>

      {/* ==================== MOBILE PALETTE DRAWER ==================== */}
      {paletteOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={() => setPaletteOpen(false)}
        >
          <div
            className="absolute bottom-0 left-0 right-0 rounded-t-2xl bg-white p-5 shadow-2xl animate-in slide-in-from-bottom-20 duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Savollar ro'yxati</h3>
              <button
                onClick={() => setPaletteOpen(false)}
                className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="mb-4 grid grid-cols-6 gap-2 sm:grid-cols-8">
              {session.questions.map((q, idx) => {
                const isAnswered = answers[q.id] !== null && answers[q.id] !== undefined;
                const isCurrent = idx === currentIdx;
                const isMarkedQ = marked.has(idx);
                return (
                  <button
                    key={q.id}
                    onClick={() => {
                      goTo(idx, idx > currentIdx ? 1 : -1);
                      setPaletteOpen(false);
                    }}
                    className={`relative flex aspect-square items-center justify-center rounded-lg text-sm font-bold transition ${
                      isCurrent
                        ? "bg-slate-900 text-white shadow-md ring-2 ring-slate-900 ring-offset-2"
                        : isAnswered
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : "bg-slate-50 text-slate-600 border border-slate-200"
                    }`}
                  >
                    {idx + 1}
                    {isMarkedQ && (
                      <span className="absolute -right-1 -top-1 size-2.5 rounded-full bg-amber-400 ring-2 ring-white" />
                    )}
                  </button>
                );
              })}
            </div>

            <div className="flex justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="size-3 rounded bg-emerald-50 border border-emerald-200" /> Javob berilgan
              </span>
              <span className="flex items-center gap-1">
                <span className="size-3 rounded bg-slate-900" /> Joriy
              </span>
              <span className="flex items-center gap-1">
                <span className="size-3 rounded bg-slate-50 border border-slate-200" /> Javobsiz
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ==================== FINISH MODAL ==================== */}
      {finishOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex size-12 items-center justify-center rounded-full bg-amber-50 text-amber-600">
                <AlertCircle className="size-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Testni yakunlash</h3>
                <p className="text-sm text-slate-500">Ishonchingiz komilmi?</p>
              </div>
            </div>

            <div className="mb-6 rounded-xl border border-slate-100 bg-slate-50 p-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-lg font-bold text-slate-900">{totalQuestions}</div>
                  <div className="text-xs text-slate-500">Jami</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-emerald-600">{answeredCount}</div>
                  <div className="text-xs text-slate-500">Javob berilgan</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-red-500">{totalQuestions - answeredCount}</div>
                  <div className="text-xs text-slate-500">Javobsiz</div>
                </div>
              </div>
            </div>

            {totalQuestions - answeredCount > 0 && (
              <p className="mb-4 text-xs text-amber-700">
                <AlertCircle className="mr-1 inline size-3" />
                Javobsiz {totalQuestions - answeredCount} ta savol qoldi. Ularga tasodifiy javob tanlanmaydi.
              </p>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setFinishOpen(false)}
                className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                Bekor qilish
              </button>
              <button
                onClick={() => handleFinish(false)}
                disabled={submitting}
                className="flex-1 rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
              >
                {submitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="size-4 animate-spin" /> Yuborilmoqda...
                  </span>
                ) : (
                  "Ha, yakunlash"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== SHORTCUTS MODAL ==================== */}
      {showShortcuts && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
          onClick={() => setShowShortcuts(false)}
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Klaviatura yorliqlari</h3>
              <button onClick={() => setShowShortcuts(false)}>
                <X className="size-5 text-slate-400" />
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between border-b border-slate-100 pb-2">
                <span className="text-slate-600">1, 2, 3, 4</span>
                <span className="font-medium text-slate-900">Variant tanlash</span>
              </div>
              <div className="flex justify-between border-b border-slate-100 pb-2">
                <span className="text-slate-600">← / →</span>
                <span className="font-medium text-slate-900">Savollar o'rtasida harakat</span>
              </div>
              <div className="flex justify-between border-b border-slate-100 pb-2">
                <span className="text-slate-600">M</span>
                <span className="font-medium text-slate-900">Belgilash</span>
              </div>
              <div className="flex justify-between border-b border-slate-100 pb-2">
                <span className="text-slate-600">L</span>
                <span className="font-medium text-slate-900">Lifeline (50/50)</span>
              </div>
              <div className="flex justify-between border-b border-slate-100 pb-2">
                <span className="text-slate-600">Ctrl + Enter</span>
                <span className="font-medium text-slate-900">Testni yakunlash</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">?</span>
                <span className="font-medium text-slate-900">Bu oynani ochish</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}