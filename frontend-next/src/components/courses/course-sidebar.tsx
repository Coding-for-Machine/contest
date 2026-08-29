"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  Lock,
  PlayCircle,
  HelpCircle,
  Layers,
  ArrowRight,
  Loader2,
  Award,
  Infinity,
  CheckCircle2,
} from "lucide-react";
import { enrollCourse } from "@/lib/api/courses";
import type { CourseDetail } from "@/lib/types/course";
import { PaymentModal } from "./payment-modal";

interface CourseSidebarProps {
  course: CourseDetail;
  isPaid: boolean;
  isLoggedIn: boolean;
}

export function CourseSidebar({
  course,
  isPaid,
  isLoggedIn,
}: CourseSidebarProps) {
  const router = useRouter();
  const { isAuthenticated } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState("");

  const progress = course.user_progress;

  const completedLessons = progress?.completed_lessons ?? 0;
  const completedTests = progress?.completed_tests ?? 0;

  const totalTasks = course.total_lessons + course.total_tests;
  const completedTasks = completedLessons + completedTests;

  const percent =
    totalTasks > 0
      ? Math.round((completedTasks / totalTasks) * 100)
      : 0;

  // 0 so'm discount ham to'g'ri ishlaydi
  const currentPrice = course.discount_price ?? course.price;
  const originalPrice =
    course.discount_price !== null ? course.price : null;

  const isFree = currentPrice <= 0;

  const handleEnroll = async () => {
    if (!isAuthenticated) {
      router.push(`/login?next=/courses/${course.slug}`);
      return;
    }

    setIsLoading(true);

    try {
      const result = await enrollCourse(course.slug);

      setIsLoading(false);

      if (result.success) {
        router.refresh();
        return;
      }

      if (result.needsPayment) {
        setPaymentAmount(
          result.amount || String(currentPrice)
        );
        setPaymentOpen(true);
        return;
      }

      alert(result.error || "Xatolik yuz berdi");
    } catch (err) {
      setIsLoading(false);
      alert("So'rovda xatolik");
    }
  };

  const firstLessonSlug =
    course.modules?.[0]?.lessons?.[0]?.slug || course.slug;

  return (
    <>
      <div className="flex flex-col gap-4">
        {/* ==================== PROGRESS ==================== */}
        {isLoggedIn && isPaid && (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-lg bg-[#C89B3C]/10">
                  <span className="text-[10px] font-bold text-[#A97920]">
                    {percent}%
                  </span>
                </div>

                <span className="text-xs font-medium text-slate-500">
                  Kurs progressi
                </span>
              </div>

              {progress?.is_completed && (
                <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-semibold text-emerald-600">
                  <CheckCircle2 className="size-3" />
                  Tugallandi
                </span>
              )}
            </div>

            <div className="px-5 py-4">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-[#C89B3C] transition-all duration-500"
                  style={{ width: `${percent}%` }}
                />
              </div>

              <div className="mt-2 flex items-center justify-between text-xs">
                <span className="text-slate-400">
                  {completedTasks} / {totalTasks} bajarildi
                </span>

                <span className="font-medium text-slate-500">
                  {percent}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ==================== CTA / PRICE ==================== */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          {/* Top bar */}
          <div className="flex items-center gap-1.5 border-b border-slate-100 bg-slate-50/70 px-5 py-3">
            <span className="size-2 rounded-full bg-red-400" />
            <span className="size-2 rounded-full bg-amber-400" />
            <span className="size-2 rounded-full bg-emerald-400" />

            <span className="ml-2 font-mono text-[10px] text-slate-400">
              course.checkout
            </span>
          </div>

          <div className="p-6">
            {/* PRICE */}
            <div className="mb-6">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-400">
                Kurs narxi
              </p>

              {isFree ? (
                <div className="flex items-center gap-2">
                  <span className="text-3xl font-bold text-[#A97920]">
                    Bepul
                  </span>

                  <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-600">
                    100% bepul
                  </span>
                </div>
              ) : (
                <div className="flex flex-col gap-1">
                  {originalPrice !== null && (
                    <span className="text-sm text-slate-400 line-through">
                      {originalPrice.toLocaleString()} so'm
                    </span>
                  )}

                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold tracking-tight text-slate-900">
                      {currentPrice.toLocaleString()}
                    </span>

                    <span className="text-sm font-medium text-slate-400">
                      so'm
                    </span>
                  </div>

                  {originalPrice !== null &&
                    originalPrice > currentPrice && (
                      <span className="mt-1 w-fit rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-500">
                        Chegirma
                      </span>
                    )}
                </div>
              )}
            </div>

            {/* FEATURES */}
            <div className="mb-6 grid grid-cols-2 gap-2.5">
              {typeof course.total_modules === "number" &&
                course.total_modules > 0 && (
                  <div className="flex items-center gap-2 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2.5">
                    <Layers className="size-4 shrink-0 text-slate-400" />

                    <span className="text-xs font-medium text-slate-600">
                      {course.total_modules} modul
                    </span>
                  </div>
                )}

              <div className="flex items-center gap-2 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2.5">
                <PlayCircle className="size-4 shrink-0 text-slate-400" />

                <span className="text-xs font-medium text-slate-600">
                  {course.total_lessons} dars
                </span>
              </div>

              <div className="flex items-center gap-2 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2.5">
                <HelpCircle className="size-4 shrink-0 text-slate-400" />

                <span className="text-xs font-medium text-slate-600">
                  {course.total_tests} test
                </span>
              </div>

              <div className="flex items-center gap-2 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2.5">
                <Award className="size-4 shrink-0 text-slate-400" />

                <span className="text-xs font-medium text-slate-600">
                  Sertifikat
                </span>
              </div>

              <div className="col-span-2 flex items-center gap-2 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2.5">
                <Infinity className="size-4 shrink-0 text-slate-400" />

                <span className="text-xs font-medium text-slate-600">
                  Doimiy dostup
                </span>

                <span className="ml-auto rounded-full bg-emerald-50 px-2 py-0.5 text-[9px] font-semibold text-emerald-600">
                  Lifetime
                </span>
              </div>
            </div>

            {/* CTA */}
            {isPaid ? (
              <Link
                href={`/courses/${course.slug}/lesson/${firstLessonSlug}`}
                className="group flex w-full items-center justify-center gap-2 rounded-xl bg-[#C89B3C] px-4 py-3.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-[#B88A2D] hover:shadow-md active:scale-[0.99]"
              >
                {percent > 0
                  ? "Davom ettirish"
                  : "Kursni boshlash"}

                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            ) : (
              <button
                onClick={handleEnroll}
                disabled={isLoading}
                className="group flex w-full items-center justify-center gap-2 rounded-xl bg-[#C89B3C] px-4 py-3.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-[#B88A2D] hover:shadow-md active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : !isAuthenticated ? (
                  <>
                    Tizimga kirish
                    <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                  </>
                ) : isFree ? (
                  <>
                    Bepul yozilish
                    <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                  </>
                ) : (
                  <>
                    <Lock className="size-4" />
                    Xarid qilish
                  </>
                )}
              </button>
            )}

            {/* PAYMENT INFO */}
            {!isPaid && !isFree && (
              <div className="mt-3 flex items-center justify-center gap-2 text-[10px] text-slate-400">
                <Lock className="size-3" />
                <span>
                  Xavfsiz to'lov · Payme / Click
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <PaymentModal
        open={paymentOpen}
        onClose={() => setPaymentOpen(false)}
        amount={paymentAmount}
        courseTitle={course.title}
      />
    </>
  );
}