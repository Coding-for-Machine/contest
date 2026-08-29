// app/tests/page.tsx
"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  Clock3,
  FileQuestion,
  Sparkles,
} from "lucide-react";

export default function TestsPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-white">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full">
          {/* Hero */}
          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="relative overflow-hidden rounded-3xl bg-[#121212] px-6 py-12 sm:px-10 sm:py-16 lg:px-16"
          >
            {/* Decorative background */}
            <div className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-[#D9AE55]/10 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-32 -left-20 size-80 rounded-full bg-white/5 blur-3xl" />

            <div className="relative mx-auto max-w-3xl text-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1, duration: 0.4 }}
                className="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-[#D9AE55]/10 ring-1 ring-inset ring-[#D9AE55]/20"
              >
                <Sparkles
                  className="size-8 text-[#D9AE55]"
                  strokeWidth={1.5}
                />
              </motion.div>

              <span className="inline-flex items-center gap-2 rounded-full bg-white/5 px-4 py-1.5 text-xs font-medium text-white/60 ring-1 ring-inset ring-white/10">
                <span className="size-1.5 animate-pulse rounded-full bg-[#D9AE55]" />
                Ishlab chiqilmoqda
              </span>

              <h1 className="mt-5 font-[var(--font-display)] text-3xl leading-tight text-white sm:text-4xl lg:text-5xl">
                Testlar bo&apos;limi
                <br />
                <span className="text-[#D9AE55]">tez orada ishga tushadi</span>
              </h1>

              <p className="mx-auto mt-5 max-w-2xl text-sm leading-7 text-white/50 sm:text-base">
                Testlar tizimi hozirda ishlab chiqilmoqda. Savollar,
                natijalar, progress va test topshirish imkoniyatlari
                tayyorlanmoqda.
              </p>

              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Link
                  href="/courses"
                  className="inline-flex items-center gap-2 rounded-xl bg-[#D9AE55] px-5 py-3 text-sm font-semibold text-[#121212] transition hover:opacity-90"
                >
                  <ArrowLeft className="size-4" />
                  Kurslarga qaytish
                </Link>

                <button
                  type="button"
                  disabled
                  className="inline-flex cursor-not-allowed items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-white/35"
                >
                  <Clock3 className="size-4" />
                  Tez orada
                </button>
              </div>
            </div>
          </motion.section>

          {/* Features */}
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <FeatureCard
              icon={<FileQuestion className="size-5" />}
              title="Testlar"
              description="Turli mavzular bo'yicha testlar va savollar."
            />

            <FeatureCard
              icon={<CheckCircle2 className="size-5" />}
              title="Natijalar"
              description="Test natijalari va o'zlashtirish ko'rsatkichlari."
            />

            <FeatureCard
              icon={<CalendarClock className="size-5" />}
              title="Vaqtli testlar"
              description="Belgilangan vaqt oralig'ida o'tkaziladigan testlar."
            />
          </div>

          {/* Development status */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, duration: 0.45 }}
            className="mx-auto mt-8 max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-start gap-4">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
                <Clock3 className="size-5" />
              </div>

              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Hozir nima bo&apos;lyapti?
                </h2>

                <p className="mt-1 text-sm leading-6 text-slate-500">
                  Test backend&apos;i va test topshirish jarayoni
                  ishlab chiqilmoqda. Tizim to&apos;liq tayyor bo&apos;lgach,
                  ushbu sahifada mavjud testlar ko&apos;rsatiladi.
                </p>
              </div>
            </div>

            <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: "55%" }}
                transition={{
                  delay: 0.4,
                  duration: 1,
                  ease: "easeOut",
                }}
                className="h-full rounded-full bg-[#D9AE55]"
              />
            </div>

            <div className="mt-2 flex items-center justify-between text-[11px] font-medium text-slate-400">
              <span>Development</span>
              <span>Backend &amp; testing</span>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
    >
      <div className="mb-4 flex size-10 items-center justify-center rounded-xl bg-slate-900 text-white">
        {icon}
      </div>

      <h3 className="text-sm font-bold text-slate-900">
        {title}
      </h3>

      <p className="mt-1.5 text-xs leading-5 text-slate-500">
        {description}
      </p>
    </motion.div>
  );
}