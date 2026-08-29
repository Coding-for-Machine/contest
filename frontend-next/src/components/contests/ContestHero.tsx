"use client";

import { motion } from "framer-motion";
import { FileQuestion, Percent, ShieldAlert } from "lucide-react";
import { Contest } from "@/lib/contests/types";
import { StatusBadge } from "./StatusBadge";
import { CountdownClock } from "./CountdownClock";
import { ContestVideoPlayer } from "./ContestVideoPlayer";
import { pluralParticipants } from "@/lib/contests/utils";

export function ContestHero({ contest }: { contest: Contest }) {
  const targetTime = contest.status === "upcoming" ? contest.start_time : contest.end_time;
  const countdownLabel =
    contest.status === "upcoming" ? "boshlanishiga qoldi" : "tugashiga qoldi";

  return (
    <section className="rounded-2xl bg-[#121212] px-6 py-8 sm:px-10 sm:py-10">
      <div className="grid gap-8 sm:grid-cols-[1.2fr_1fr] sm:gap-10">
        <div className="flex flex-col justify-between">
          <div>
            <StatusBadge status={contest.status} tone="dark" />
            <motion.h1
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: "easeOut" }}
              className="mt-4 font-[var(--font-display)] text-3xl leading-[1.15] text-white sm:text-4xl"
            >
              {contest.title}
            </motion.h1>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-white/55">
              {contest.description}
            </p>

            <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-xs text-white/45">
              <span className="flex items-center gap-1.5">
                <FileQuestion size={14} strokeWidth={1.75} aria-hidden />
                {contest.questions_count} savol
              </span>
              <span className="flex items-center gap-1.5">
                <Percent size={14} strokeWidth={1.75} aria-hidden />
                O'tish balli {contest.pass_score_percent}%
              </span>
              <span className="flex items-center gap-1.5">
                <ShieldAlert size={14} strokeWidth={1.75} aria-hidden />
                Jarima {Math.round(contest.penalty_coefficient * 100)}%
              </span>
              <span>{pluralParticipants(contest.participants_count)}</span>
            </div>
          </div>

          <div className="mt-8">
            <CountdownClock target={targetTime} label={countdownLabel} />
            <div className="mt-6 flex gap-3">
              <button className="rounded-lg bg-[#D9AE55] px-5 py-2.5 text-sm font-medium text-[#121212] transition-opacity hover:opacity-90">
                {contest.status === "ended" ? "Natijalarni ko'rish" : "Tanlovga qo'shilish"}
              </button>
              <a
                href={`/contests/${contest.slug}`}
                className="rounded-lg border border-white/15 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/5"
              >
                Batafsil
              </a>
            </div>
          </div>
        </div>

        <ContestVideoPlayer video={contest.intro_video} title={contest.title} dark />
      </div>
    </section>
  );
}