"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import confetti from "canvas-confetti";
import { PartyPopper, X, ArrowRight } from "lucide-react";

interface LessonCompleteModalProps {
  open: boolean;
  onClose: () => void;
  lessonTitle: string;
  totalTasks: number;
  earnedXp: number;
  nextHref?: string | null;
}

export function LessonCompleteModal({
  open,
  onClose,
  lessonTitle,
  totalTasks,
  earnedXp,
  nextHref,
}: LessonCompleteModalProps) {
  const mounted = useRef(false);
  const firedRef = useRef(false);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!open) {
      firedRef.current = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }

    if (firedRef.current) return;
    firedRef.current = true;

    confetti({
      particleCount: 120,
      spread: 90,
      startVelocity: 45,
      origin: { y: 0.6 },
      colors: ["#111827", "#f59e0b", "#16a34a"],
    });

    const end = Date.now() + 1800;

    const frame = () => {
      confetti({
        particleCount: 3,
        angle: 60,
        spread: 60,
        origin: { x: 0, y: 0.75 },
        colors: ["#111827", "#f59e0b", "#16a34a"],
      });
      confetti({
        particleCount: 3,
        angle: 120,
        spread: 60,
        origin: { x: 1, y: 0.75 },
        colors: ["#111827", "#f59e0b", "#16a34a"],
      });

      if (Date.now() < end) {
        rafRef.current = requestAnimationFrame(frame);
      }
    };

    rafRef.current = requestAnimationFrame(frame);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [open]);

  // Escape bilan yopish
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!mounted.current || !open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Yopish"
        onClick={onClose}
        className="absolute inset-0 bg-neutral-900/45 backdrop-blur-sm"
      />

      <div className="relative w-full max-w-md overflow-hidden rounded-3xl bg-white p-8 text-center shadow-2xl animate-in zoom-in-95 fade-in duration-200">
        <button
          type="button"
          onClick={onClose}
          aria-label="Yopish"
          className="absolute right-4 top-4 flex size-8 items-center justify-center rounded-full text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
        >
          <X className="size-4" />
        </button>

        <div className="mx-auto mb-5 flex size-16 items-center justify-center rounded-full bg-neutral-900 text-white shadow-lg shadow-neutral-900/20">
          <PartyPopper className="size-7" />
        </div>

        <h2 className="text-xl font-bold tracking-tight text-neutral-900">
          Tabriklaymiz!
        </h2>

        <p className="mt-2 text-sm leading-relaxed text-neutral-500">
          Siz{" "}
          <span className="font-semibold text-neutral-800">
            {lessonTitle}
          </span>{" "}
          darsidagi barcha {totalTasks} ta vazifani muvaffaqiyatli
          yakunladingiz.
        </p>

        {earnedXp > 0 && (
          <div className="mx-auto mt-5 inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-4 py-1.5 text-sm font-semibold text-neutral-700">
            +{earnedXp} XP jamlandi
          </div>
        )}

        <div className="mt-7 flex flex-col gap-2">
          {nextHref ? (
            <Link
              href={nextHref}
              className="flex h-11 w-full items-center justify-center gap-1.5 rounded-xl bg-neutral-900 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
            >
              Keyingi darsga o&apos;tish
              <ArrowRight className="size-4" />
            </Link>
          ) : null}

          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-full items-center justify-center rounded-xl border border-neutral-200 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
          >
            {nextHref ? "Shu darsda qolish" : "Yopish"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}