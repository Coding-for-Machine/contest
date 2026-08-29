"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetcher } from "@/lib/utils";
import type { ReviewResponse, ReviewQuestion } from "@/lib/tests/types";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { VideoPlayer } from "@/components/VideoPlayer";
import { Skeleton } from "@/components/ui/skeleton";
import confetti from "canvas-confetti";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  MinusCircle,
  PartyPopper,
  Frown,
  Zap,
  Clock,
  Lightbulb,
  VideoIcon,
  Volume2,
  VolumeX,
  Sparkles,
  Trophy,
  Medal,
  Crown,
  Star,
  Gift,
  Flame,
  Music,
  ChevronDown,
  ChevronUp,
  Share2,
  Download,
  Target,
  Calendar,
  TrendingUp,
  Award,
  Gem,
  Rocket,
  Info,
  Play,
  Brain,
  BarChart3,
  Users,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  FileText,
  BookOpen,
  GraduationCap,
  Check,
  AlertCircle,
  Timer,
} from "lucide-react";
import { XPButton } from "@/components/Xp";

/* ================================================================
   HELPERS
   ================================================================ */

/**
 * Sanani formatlash
 * @param dateStr - ISO date string yoki null
 * @returns Formatlangan sana yoki "—"
 */
function fmtDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleString("uz-UZ", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

/**
 * Savol holatini aniqlash
 * @param q - ReviewQuestion obyekti
 * @returns "correct" | "wrong" | "unanswered"
 */
function questionStatus(q: ReviewQuestion): "correct" | "wrong" | "unanswered" {
  if (q.chosen_choice_id === null || q.chosen_choice_id === undefined) return "unanswered";
  return q.is_correct ? "correct" : "wrong";
}

/**
 * Natija rangini aniqlash
 */
function getResultColor(passed: boolean, percentage: number): string {
  if (passed) return "text-emerald-600";
  if (percentage >= 40) return "text-amber-600";
  return "text-red-600";
}

/**
 * Natija matnini olish
 */
function getResultText(passed: boolean, percentage: number): string {
  if (passed) return "✅ Muvaffaqiyatli o'tdingiz!";
  if (percentage >= 40) return "⚠️ Yaqin edingiz, yana urinib ko'ring!";
  return "❌ Ko'proq tayyorgarlik kerak!";
}

/* ================================================================
   ANIMATED BACKGROUND
   ================================================================ */

/**
 * Animatsion fon komponenti
 * @param passed - Testdan o'tilganmi?
 */
function AnimatedBackground({ passed }: { passed: boolean }) {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Gradient orbs */}
      <motion.div
        animate={{
          x: [0, 100, 0, -100, 0],
          y: [0, -100, 0, 100, 0],
          scale: [1, 1.2, 1, 1.3, 1],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "linear",
        }}
        className={`absolute top-10 left-10 w-96 h-96 rounded-full blur-3xl ${
          passed ? "bg-emerald-200/20" : "bg-red-200/20"
        }`}
      />
      <motion.div
        animate={{
          x: [0, -80, 0, 80, 0],
          y: [0, 80, 0, -80, 0],
          scale: [1, 1.3, 1, 1.1, 1],
        }}
        transition={{
          duration: 25,
          repeat: Infinity,
          ease: "linear",
          delay: 2,
        }}
        className={`absolute bottom-10 right-10 w-80 h-80 rounded-full blur-3xl ${
          passed ? "bg-blue-200/20" : "bg-orange-200/20"
        }`}
      />
      <motion.div
        animate={{
          x: [0, 60, 0, -60, 0],
          y: [0, -60, 0, 60, 0],
          scale: [1, 1.1, 1, 1.2, 1],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "linear",
          delay: 4,
        }}
        className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full blur-3xl ${
          passed ? "bg-violet-200/15" : "bg-amber-200/15"
        }`}
      />

      {/* Floating particles */}
      {[...Array(30)].map((_, i) => (
        <motion.div
          key={i}
          animate={{
            y: [0, -100, 0],
            x: [0, Math.random() * 100 - 50, 0],
            opacity: [0, 0.5, 0],
          }}
          transition={{
            duration: Math.random() * 10 + 10,
            repeat: Infinity,
            delay: Math.random() * 10,
            ease: "linear",
          }}
          className={`absolute w-1 h-1 rounded-full ${
            passed ? "bg-emerald-400" : "bg-red-400"
          }`}
          style={{
            left: Math.random() * 100 + "%",
            top: Math.random() * 100 + "%",
          }}
        />
      ))}
    </div>
  );
}

/* ================================================================
   CONFETTI FIREWORKS
   ================================================================ */

/**
 * Konfeti festival komponenti
 * @param active - Faolmi?
 */
function ConfettiFireworks({ active }: { active: boolean }) {
  const [isMuted, setIsMuted] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [particleCount, setParticleCount] = useState(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Bayram musiqasini ijro etish
   */
  const playCelebrationSound = useCallback(async () => {
    if (isMuted) return;

    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }

      const ctx = audioContextRef.current;
      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      // 12 notali bayram kuyi
      const melody = [
        { freq: 523.25, duration: 0.12 }, // C5
        { freq: 659.25, duration: 0.12 }, // E5
        { freq: 783.99, duration: 0.12 }, // G5
        { freq: 1046.5, duration: 0.2 }, // C6
        { freq: 987.77, duration: 0.12 }, // B5
        { freq: 880.0, duration: 0.12 }, // A5
        { freq: 783.99, duration: 0.12 }, // G5
        { freq: 659.25, duration: 0.2 }, // E5
        { freq: 1046.5, duration: 0.15 }, // C6
        { freq: 1318.51, duration: 0.15 }, // E6
        { freq: 1567.98, duration: 0.3 }, // G6
        { freq: 1046.5, duration: 0.4 }, // C6
      ];

      for (let i = 0; i < melody.length; i++) {
        const note = melody[i];
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);
        oscillator.type = "sine";
        oscillator.frequency.value = note.freq;

        // Harmonik (uchinchi interval)
        const harmonic = ctx.createOscillator();
        const harmonicGain = ctx.createGain();
        harmonic.connect(harmonicGain);
        harmonicGain.connect(ctx.destination);
        harmonic.type = "triangle";
        harmonic.frequency.value = note.freq * 1.25;
        harmonicGain.gain.setValueAtTime(0.06, ctx.currentTime);

        const startTime = ctx.currentTime + i * 0.08;
        gainNode.gain.setValueAtTime(0.25, startTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + note.duration);
        harmonicGain.gain.setValueAtTime(0.06, startTime);
        harmonicGain.gain.exponentialRampToValueAtTime(0.002, startTime + note.duration);

        oscillator.start(startTime);
        oscillator.stop(startTime + note.duration);
        harmonic.start(startTime);
        harmonic.stop(startTime + note.duration);
      }

      await new Promise((resolve) => setTimeout(resolve, melody.length * 80 + 500));
    } catch (err) {
      console.log("Audio play failed:", err);
    }
  }, [isMuted]);

  /**
   * Konfetilarni uchirish
   */
  const launchConfetti = useCallback(() => {
    const duration = 6 * 1000;
    const animationEnd = Date.now() + duration;
    const defaults = {
      startVelocity: 35,
      spread: 360,
      ticks: 80,
      zIndex: 9999,
      colors: [
        "#2563eb", "#7c3aed", "#ec4899", "#f59e0b",
        "#10b981", "#ef4444", "#8b5cf6", "#06b6d4",
        "#f472b6", "#34d399", "#fbbf24", "#60a5fa",
        "#a78bfa", "#f87171", "#34d399", "#fcd34d",
        "#67e8f9", "#c084fc", "#fb923c", "#22d3ee",
      ],
    };

    const randomInRange = (min: number, max: number) =>
      Math.random() * (max - min) + min;

    let intervalCount = 0;
    const maxIntervals = 30;
    let totalParticles = 0;

    if (intervalRef.current) clearInterval(intervalRef.current);

    intervalRef.current = setInterval(() => {
      const timeLeft = animationEnd - Date.now();
      intervalCount++;

      if (timeLeft <= 0 || intervalCount > maxIntervals) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setIsPlaying(false);
        setProgress(100);
        return;
      }

      const progressPercent = (intervalCount / maxIntervals) * 100;
      setProgress(Math.min(progressPercent, 100));

      const baseCount = Math.min(70, 20 + (timeLeft / duration) * 60);
      totalParticles += baseCount * 3;
      setParticleCount(totalParticles);

      // Chap tomondan
      confetti({
        ...defaults,
        particleCount: baseCount * 0.3,
        origin: { x: randomInRange(0, 0.25), y: randomInRange(0.1, 0.7) },
        angle: randomInRange(50, 130),
        spread: randomInRange(60, 140),
      });

      // O'ng tomondan
      confetti({
        ...defaults,
        particleCount: baseCount * 0.3,
        origin: { x: randomInRange(0.75, 1), y: randomInRange(0.1, 0.7) },
        angle: randomInRange(50, 130),
        spread: randomInRange(60, 140),
      });

      // Tepadan
      confetti({
        ...defaults,
        particleCount: baseCount * 0.25,
        origin: { x: randomInRange(0.35, 0.65), y: randomInRange(0, 0.15) },
        angle: randomInRange(60, 120),
        spread: randomInRange(100, 180),
        startVelocity: randomInRange(40, 60),
      });

      // Pastdan
      confetti({
        ...defaults,
        particleCount: baseCount * 0.15,
        origin: { x: randomInRange(0.2, 0.8), y: randomInRange(0.85, 1) },
        angle: randomInRange(-30, 30),
        spread: randomInRange(60, 120),
        startVelocity: randomInRange(20, 40),
      });

      // Yulduzchalar
      confetti({
        ...defaults,
        particleCount: baseCount * 0.2,
        startVelocity: randomInRange(50, 80),
        spread: 200,
        origin: { x: randomInRange(0.1, 0.9), y: randomInRange(0.1, 0.4) },
        colors: ["#ffffff", "#fbbf24", "#f472b6", "#34d399"],
      });

      // Katta portlash
      if (intervalCount % 3 === 0) {
        confetti({
          ...defaults,
          particleCount: baseCount * 0.5,
          spread: randomInRange(150, 250),
          origin: { x: randomInRange(0.2, 0.8), y: randomInRange(0.2, 0.6) },
          startVelocity: randomInRange(40, 70),
          colors: ["#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#10b981", "#3b82f6"],
        });
      }
    }, 180);

    // Dastlabki katta portlashlar
    setTimeout(() => {
      confetti({
        ...defaults,
        particleCount: 120,
        spread: 200,
        origin: { x: 0.5, y: 0.25 },
        startVelocity: 50,
      });
    }, 100);

    setTimeout(() => {
      confetti({
        ...defaults,
        particleCount: 100,
        spread: 180,
        origin: { x: 0.2, y: 0.35 },
        startVelocity: 45,
        angle: 45,
      });
    }, 300);

    setTimeout(() => {
      confetti({
        ...defaults,
        particleCount: 100,
        spread: 180,
        origin: { x: 0.8, y: 0.35 },
        startVelocity: 45,
        angle: 135,
      });
    }, 300);

    setTimeout(() => {
      confetti({
        ...defaults,
        particleCount: 80,
        spread: 150,
        origin: { x: 0.5, y: 0.8 },
        startVelocity: 30,
        angle: -90,
      });
    }, 500);
  }, []);

  // Active bo'lganda ishga tushirish
  useEffect(() => {
    if (active) {
      setIsPlaying(true);
      setProgress(0);
      setParticleCount(0);

      const start = async () => {
        await playCelebrationSound();
        launchConfetti();
      };
      start();

      const timer = setTimeout(() => {
        setIsPlaying(false);
        setProgress(100);
        if (intervalRef.current) clearInterval(intervalRef.current);
      }, 7000);

      return () => {
        clearTimeout(timer);
        if (intervalRef.current) clearInterval(intervalRef.current);
      };
    }
  }, [active, playCelebrationSound, launchConfetti]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  if (!active) return null;

  return (
    <motion.div
      initial={{ x: 100, opacity: 0, y: 50 }}
      animate={{ x: 0, opacity: 1, y: 0 }}
      exit={{ x: 100, opacity: 0, y: 50 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="fixed bottom-6 right-6 z-50 flex items-center gap-3 bg-white/95 backdrop-blur rounded-2xl shadow-2xl border border-slate-200 p-4 min-w-[200px]"
    >
      <div className="flex items-center gap-3">
        <motion.div
          animate={isPlaying ? { rotate: 360 } : {}}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          className="relative"
        >
          <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 flex items-center justify-center shadow-lg">
            {isPlaying ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <PartyPopper className="w-5 h-5 text-white" />
            )}
          </div>
          {isPlaying && (
            <motion.div
              animate={{ scale: [1, 1.5, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
              className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full"
            />
          )}
        </motion.div>

        <div>
          <div className="text-sm font-bold text-slate-900">
            {isPlaying ? "🎊 Festival!" : "✅ Tugadi!"}
          </div>
          <div className="flex items-center gap-2">
            <div className="w-20 h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-500 via-violet-500 to-pink-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <span className="text-[10px] font-mono text-slate-400">{Math.round(progress)}%</span>
          </div>
          {isPlaying && (
            <div className="text-[9px] text-slate-400">
              {particleCount.toLocaleString()} ta konfeti
            </div>
          )}
        </div>

        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setIsMuted(!isMuted)}
          className="p-2 rounded-xl hover:bg-slate-100 transition-colors"
        >
          {isMuted ? (
            <VolumeX className="w-4 h-4 text-slate-500" />
          ) : (
            <Volume2 className="w-4 h-4 text-blue-600" />
          )}
        </motion.button>
      </div>
    </motion.div>
  );
}


/* ================================================================
   MAIN PAGE
   ================================================================ */

/**
 * Test natijalari tahlil sahifasi
 */
export default function ReviewPage() {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const [showConfetti, setShowConfetti] = useState(false);
  const [showTooltip, setShowTooltip] = useState(true);
  const [collectedXP, setCollectedXP] = useState(0);

  // SWR orqali ma'lumotlarni olish
  const { data: review, error, isLoading } = useSWR<ReviewResponse>(
    sessionId ? `/api/test-session/session/${sessionId}/review` : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  // Muvaffaqiyatli bo'lsa konfetini ko'rsatish
  useEffect(() => {
    if (review?.passed) {
      setShowConfetti(true);
    }
  }, [review]);

  // Tooltip oldin ko'rsatilganmi tekshirish
  useEffect(() => {
    const hasSeen = localStorage.getItem("review_tooltip_seen");
    if (hasSeen) {
      setShowTooltip(false);
    }
  }, []);

  const handleDismissTooltip = () => {
    localStorage.setItem("review_tooltip_seen", "true");
    setShowTooltip(false);
  };

  // XP yig'ish
  const handleCollectXP = (amount: number) => {
    setCollectedXP(prev => prev + amount);
    console.log(`🎉 +${amount} XP collected! Total: ${collectedXP + amount}`);
  };

  // Yuklanayotganda
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  // Xatolik yoki ma'lumot yo'q
  if (error || !review) {
    return <ErrorState />;
  }

  const passed = review.passed;
  const percentage = review.percentage;

  return (
    <main className="relative min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      {/* Animatsion fon */}
      <AnimatedBackground passed={passed} />

      {/* Konfeti festivali */}
      <AnimatePresence>
        <ConfettiFireworks active={showConfetti} />
      </AnimatePresence>

      {/* Muvaffaqiyatli banner */}
      {passed && (
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="relative overflow-hidden bg-gradient-to-r from-blue-600 via-violet-600 to-pink-500 animate-gradient"
        >
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyek0zNiAyNHYySDI0di0yaDEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-20" />
          <div className="relative mx-auto max-w-4xl px-4 py-4 sm:py-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <motion.div
                  animate={{ rotate: [0, 360] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  className="flex h-12 w-12 items-center justify-center rounded-full bg-white/20 backdrop-blur shadow-lg"
                >
                  <Trophy className="h-6 w-6 text-white" />
                </motion.div>
                <div>
                  <h2 className="flex items-center gap-2 text-lg font-bold text-white sm:text-xl">
                    Tabriklaymiz! Test muvaffaqiyatli yakunlandi
                    <motion.span
                      animate={{ scale: [1, 1.3, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    >
                      <Sparkles className="h-5 w-5 text-yellow-300" />
                    </motion.span>
                  </h2>
                  <p className="text-sm text-blue-100">
                    Siz {Math.round(percentage)}% natija bilan o'tdingiz • {review.xp_earned} XP qo'lga kiritdingiz
                  </p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      <div className="mx-auto max-w-7xl px-4 py-6 sm:py-8">
        {/* Orqaga qaytish */}
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="flex items-center justify-between"
        >
          <Link
            href="/tests"
            className="group inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 transition hover:bg-white/80 hover:text-slate-900 hover:shadow-sm"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
            Testlar ro'yxatiga qaytish
          </Link>
          
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="flex items-center gap-2 text-xs text-slate-400"
          >
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Savol ustiga bosing — tahlil ochiladi</span>
          </motion.div>
        </motion.div>


        {/* ===== NATIJA SARLAVHASI ===== */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative mb-8 overflow-hidden rounded-2xl border bg-white/80 backdrop-blur-sm shadow-lg shadow-slate-200/50"
        >
          <div
            className={`p-6 sm:p-8 ${
              passed
                ? "bg-gradient-to-br from-emerald-50/70 via-white/80 to-white/80"
                : "bg-gradient-to-br from-red-50/70 via-white/80 to-white/80"
            }`}
          >
            {/* Dekorativ elementlar */}
            {passed && (
              <>
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 3, repeat: Infinity }}
                  className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-emerald-200/20 blur-3xl"
                />
                <motion.div
                  animate={{ scale: [1, 1.3, 1] }}
                  transition={{ duration: 4, repeat: Infinity, delay: 0.5 }}
                  className="absolute -bottom-10 -left-10 h-40 w-40 rounded-full bg-blue-200/20 blur-3xl"
                />
              </>
            )}

            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              {/* Foiz ko'rsatkichi */}
              <div className="flex items-center gap-6">
                <motion.div
                  whileHover={{ scale: 1.05, rotate: 5 }}
                  whileTap={{ scale: 0.95 }}
                  className={`relative flex h-24 w-24 shrink-0 items-center justify-center rounded-full border-4 sm:h-28 sm:w-28 ${
                    passed
                      ? "border-emerald-500 bg-gradient-to-br from-emerald-50 to-white text-emerald-600"
                      : "border-red-500 bg-gradient-to-br from-red-50 to-white text-red-600"
                  }`}
                >
                  {passed && (
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="absolute -right-1 -top-1"
                    >
                      <Sparkles className="h-6 w-6 text-amber-400" />
                    </motion.div>
                  )}
                  <span className="font-mono text-3xl font-bold sm:text-4xl">
                    {Math.round(percentage)}%
                  </span>
                </motion.div>

                <div>
                  <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 sm:text-3xl">
                    {passed ? (
                      <>
                        <motion.span
                          animate={{ rotate: [0, 15, -15, 0] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        >
                          <PartyPopper className="h-7 w-7 text-amber-500" />
                        </motion.span>
                        Tabriklaymiz!
                      </>
                    ) : (
                      <>
                        <Frown className="h-7 w-7 text-slate-400" />
                        Afsuski, o'tolmadingiz
                      </>
                    )}
                  </h1>
                  <p className="mt-1 text-sm text-slate-500 sm:text-base">
                    {review.test_title}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-400 sm:text-sm">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      {fmtDate(review.started_at)}
                    </span>
                    <span className="hidden sm:inline">•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {fmtDate(review.completed_at)}
                    </span>
                    <span className="hidden sm:inline">•</span>
                    <span className="flex items-center gap-1">
                      <Timer className="h-3.5 w-3.5" />
                      <span>Sessiya: {review.session_id.slice(0, 8)}...</span>
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={`text-sm font-medium ${getResultColor(passed, percentage)}`}>
                      {getResultText(passed, percentage)}
                    </span>
                    <span className="text-xs text-slate-400">
                      (Status: {review.status})
                    </span>
                  </div>
                </div>
              </div>

              {/* XP va Bonus - XPButton qo'shildi */}
              <div className="flex flex-wrap items-center gap-3">
                {/* XP Button - animatsiyali, oltin rangda */}
                <XPButton 
                  xpAmount={review.xp_earned} 
                  size="md"
                  onCollect={handleCollectXP}
                />
                
                {passed && (
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-700"
                  >
                    <Gift className="h-4 w-4" />
                    +50 Bonus
                  </motion.div>
                )}
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600"
                >
                  <Award className="h-4 w-4" />
                  {review.score} ball
                </motion.div>
              </div>
            </div>

            {/* Yig'ilgan XP ko'rsatkichi */}
            {collectedXP > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-3 text-center text-sm"
              >
                <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">
                  <Zap className="h-3 w-3" />
                  Yig'ilgan XP: <strong>{collectedXP}</strong>
                </span>
              </motion.div>
            )}

            {/* Statistika bloki */}
            <motion.div
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 24 }}
              className="relative mt-6 grid grid-cols-3 gap-3 sm:gap-4"
            >
              <StatBox
                icon={<CheckCircle2 className="h-4 w-4" />}
                value={review.correct_count}
                label="to'g'ri"
                tone="emerald"
              />
              <StatBox
                icon={<XCircle className="h-4 w-4" />}
                value={review.wrong_count}
                label="xato"
                tone="red"
              />
              <StatBox
                icon={<MinusCircle className="h-4 w-4" />}
                value={review.unanswered_count}
                label="javobsiz"
                tone="slate"
              />
            </motion.div>

            {/* Yutuqlar */}
            {passed && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="relative mt-4 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4"
              >
                <span className="text-xs font-medium text-slate-400">🏆 Yutuqlar:</span>
                <div className="flex flex-wrap gap-2">
                  {percentage >= 80 && (
                    <motion.span
                      whileHover={{ scale: 1.05 }}
                      className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700"
                    >
                      <Crown className="h-3 w-3" /> A'lo
                    </motion.span>
                  )}
                  {percentage >= 60 && percentage < 80 && (
                    <motion.span
                      whileHover={{ scale: 1.05 }}
                      className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700"
                    >
                      <Star className="h-3 w-3" /> Yaxshi
                    </motion.span>
                  )}
                  {review.correct_count === review.questions.length && (
                    <motion.span
                      whileHover={{ scale: 1.05 }}
                      className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-700"
                    >
                      <Medal className="h-3 w-3" /> Mukammal
                    </motion.span>
                  )}
                  <motion.span
                    whileHover={{ scale: 1.05 }}
                    className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-3 py-1 text-xs font-medium text-violet-700"
                  >
                    <Flame className="h-3 w-3" /> +{review.xp_earned} XP
                  </motion.span>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* ===== SAVOLLAR RO'YXATI ===== */}
        <div className="space-y-4">
          {review.questions.map((q, idx) => (
            <motion.div
              key={q.id}
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ 
                type: "spring", 
                stiffness: 400, 
                damping: 30,
                delay: idx * 0.05 
              }}
            >
              <QuestionReviewCard question={q} index={idx} />
            </motion.div>
          ))}
        </div>
          
        {/* ===== PASTKI TUGMALAR ===== */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-4 mb-26 flex flex-wrap items-center justify-center gap-4 border-t border-slate-200 pt-4"
        >
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <Link
              href="/tests"
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              <ArrowLeft className="h-4 w-4" />
              Boshqa testlar
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </main>
  );
}

/* ================================================================
   LOADING SKELETON
   ================================================================ */

/**
 * Yuklanayotganda ko'rsatiladigan skeleton
 */
function LoadingSkeleton() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Skeleton className="mb-6 h-6 w-32" />
        <Skeleton className="mb-8 h-48 w-full rounded-2xl" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      </div>
    </main>
  );
}

/* ================================================================
   ERROR STATE
   ================================================================ */

/**
   * Xatolik holati
   */
function ErrorState() {
  const params = useParams<{ id: string }>();
  return (
    <motion.main
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="flex min-h-screen flex-col items-center justify-center px-4 text-center"
    >
      <XCircle className="mb-4 h-14 w-14 text-slate-300" strokeWidth={1.2} />
      <h3 className="text-xl font-bold text-slate-900">Tahlil topilmadi</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        Bu tahlil faqat yakunlangan seanslar uchun mavjud, yoki havola noto'g'ri.
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Sessiya ID: <span className="font-mono">{params?.id?.slice(0, 12)}...</span>
      </p>
      <Link
        href="/tests"
        className="mt-6 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
      >
        Testlar ro'yxati
      </Link>
    </motion.main>
  );
}

/* ================================================================
   STAT BOX
   ================================================================ */

/**
 * Statistika ko'rsatkichi
 */
function StatBox({
  icon,
  value,
  label,
  tone,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
  tone: "emerald" | "red" | "slate";
}) {
  const toneMap = {
    emerald: "bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
    red: "bg-red-50 text-red-700 hover:bg-red-100",
    slate: "bg-slate-100 text-slate-600 hover:bg-slate-200",
  };

  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className={`flex flex-col items-center gap-1 rounded-xl p-3 transition sm:p-4 ${toneMap[tone]}`}
    >
      <span className="flex items-center gap-1 text-xs font-medium opacity-80">
        {icon}
        {label}
      </span>
      <span className="font-mono text-xl font-bold sm:text-2xl">{value}</span>
    </motion.div>
  );
}

/* ================================================================
   QUESTION REVIEW CARD
   ================================================================ */

/**
 * Bitta savol tahlili kartasi
 */
function QuestionReviewCard({ question, index }: { question: ReviewQuestion; index: number }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const status = questionStatus(question);

  const statusConfig = {
    correct: {
      icon: <CheckCircle2 className="h-5 w-5 text-emerald-600" />,
      ring: "border-emerald-200 hover:border-emerald-300",
      chip: "bg-emerald-50 text-emerald-700 border-emerald-200",
      label: "To'g'ri",
    },
    wrong: {
      icon: <XCircle className="h-5 w-5 text-red-600" />,
      ring: "border-red-200 hover:border-red-300",
      chip: "bg-red-50 text-red-700 border-red-200",
      label: "Xato",
    },
    unanswered: {
      icon: <MinusCircle className="h-5 w-5 text-slate-400" />,
      ring: "border-slate-200 hover:border-slate-300",
      chip: "bg-slate-100 text-slate-500 border-slate-200",
      label: "Javobsiz",
    },
  }[status];

  const hasExplanation = question.explanation || question.explanation_video;

  // To'g'ri javob matnini topish
  const correctChoice = question.choices.find(c => c.is_correct);
  const chosenChoice = question.choices.find(c => c.is_chosen);

  return (
    <motion.div
      layout
      className={`overflow-hidden rounded-xl border-2 bg-white/90 backdrop-blur-sm transition-all hover:shadow-xl ${statusConfig.ring}`}
    >
      {/* Sarlavha */}
      <motion.div
        className="flex cursor-pointer items-center justify-between gap-2 px-5 py-3 transition hover:bg-slate-50/70"
        onClick={() => hasExplanation && setIsExpanded(!isExpanded)}
        whileHover={{ backgroundColor: "rgba(241, 245, 249, 0.5)" }}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs font-semibold text-slate-400">
            Savol {index + 1}
          </span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border-2 px-2.5 py-0.5 text-xs font-medium ${statusConfig.chip}`}
          >
            {statusConfig.icon}
            {statusConfig.label}
          </span>
          {/* Qisqa ma'lumot */}
          {status === "correct" && (
            <span className="text-[10px] text-emerald-400">✓</span>
          )}
          {status === "wrong" && (
            <span className="text-[10px] text-red-400">✗</span>
          )}
          {status === "unanswered" && (
            <span className="text-[10px] text-slate-400">-</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Javob ID si */}
          <span className="text-[10px] text-slate-400 font-mono">
            ID: {question.id}
          </span>
          {hasExplanation && (
            <motion.button
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.3 }}
              className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            >
              <ChevronDown className="h-4 w-4" />
            </motion.button>
          )}
        </div>
      </motion.div>

      {/* Savol matni */}
      <div className="px-5 pt-4">
        <div className="flex items-start gap-2">
          <div className="mt-1">
            <FileText className="h-4 w-4 text-slate-400" />
          </div>
          <div className="flex-1">
            <MarkdownRenderer content={question.text} />
          </div>
        </div>
      </div>

      {/* Javob variantlari */}
      <div className="space-y-2 px-5 pb-4 pt-3">
        {question.choices.map((choice, cIdx) => {
          let cls =
            "flex items-start gap-3 rounded-lg border-2 px-3.5 py-2.5 text-sm transition-all ";
          let icon: React.ReactNode = null;

          if (choice.is_correct) {
            cls += "border-emerald-300 bg-emerald-50";
            icon = <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />;
          } else if (choice.is_chosen && !choice.is_correct) {
            cls += "border-red-300 bg-red-50";
            icon = <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />;
          } else {
            cls += "border-slate-200 bg-slate-50/50 hover:border-slate-300";
          }

          return (
            <motion.div
              key={choice.id}
              whileHover={!choice.is_correct && !choice.is_chosen ? { scale: 1.01 } : {}}
              className={cls}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                  choice.is_correct
                    ? "bg-emerald-500 text-white"
                    : choice.is_chosen
                      ? "bg-red-500 text-white"
                      : "bg-slate-200 text-slate-500"
                }`}
              >
                {String.fromCharCode(65 + cIdx)}
              </span>
              <span className="flex-1 whitespace-pre-wrap pt-0.5 text-slate-800">
                {choice.text}
              </span>
              {icon}
              {choice.is_chosen && (
                <span className="shrink-0 rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                  Sizning javobingiz
                </span>
              )}
              {choice.is_correct && !choice.is_chosen && (
                <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
                  To'g'ri javob
                </span>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Tahlil - yig'iluvchi */}
      {hasExplanation && (
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="border-t border-slate-100 bg-gradient-to-br from-slate-50/80 to-white px-5 py-4">
                {/* Matnli izoh */}
                {question.explanation && (
                  <div className="mb-3 flex items-start gap-2">
                    <motion.div
                      animate={{ rotate: [0, 10, -10, 0] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <Lightbulb className="mt-1 h-4 w-4 shrink-0 text-amber-500" />
                    </motion.div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            Izoh
                        </p>
                        <motion.div
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        >
                          <Info className="h-3 w-3 text-blue-400" />
                        </motion.div>
                      </div>
                      <MarkdownRenderer content={question.explanation} />
                    </div>
                  </div>
                )}

                {/* Video tahlil */}
                {question.explanation_video?.hls && (
                  <div className="mt-2">
                    <div className="flex items-center gap-2 mb-2">
                      <motion.div
                        animate={{ scale: [1, 1.3, 1] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      >
                        <VideoIcon className="h-4 w-4 text-violet-500" />
                      </motion.div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                         Video tahlil
                      </p>
                      <motion.div
                        animate={{ x: [0, 5, 0] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        <Play className="h-3 w-3 text-violet-400" />
                      </motion.div>
                    </div>
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.4 }}
                      className="overflow-hidden rounded-lg shadow-lg"
                    >
                      <VideoPlayer
                        src={question.explanation_video.hls}
                        poster={question.explanation_video.img || undefined}
                      />
                    </motion.div>
                  </div>
                )}

                {/* Qo'shimcha ma'lumot */}
                <div className="mt-3 flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100 text-[10px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <Check className="h-3 w-3 text-emerald-400" />
                    To'g'ri javob: {correctChoice ? String.fromCharCode(65 + question.choices.indexOf(correctChoice)) : "—"}
                  </span>
                  <span className="flex items-center gap-1">
                    <AlertCircle className="h-3 w-3 text-slate-400" />
                    Sizning javob: {chosenChoice ? String.fromCharCode(65 + question.choices.indexOf(chosenChoice)) : "Javobsiz"}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3 text-slate-400" />
                    Savol ID: {question.id}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </motion.div>
  );
}

// ============================================================
// GLOBAL STYLES - app/globals.css ga qo'shing
// ============================================================
/*
@keyframes gradient {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
.animate-gradient {
  animation: gradient 8s ease-in-out infinite;
}
*/