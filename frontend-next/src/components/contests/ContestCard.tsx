"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { FileQuestion, Users, ArrowUpRight, Award } from "lucide-react";
import { Contest } from "@/lib/contests/types";
import { formatDateUz, pluralParticipants } from "@/lib/contests/utils";
import { StatusBadge, TypeTag } from "./StatusBadge";

export function ContestCard({ contest, index }: { contest: Contest; index: number }) {
  const thumb = contest.intro_video?.thumbnail ?? contest.cover_image;
  const isEnded = contest.status === "ended";

  return (
    <motion.a
      href={`/contests/${contest.slug}`}
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4, delay: index * 0.05, ease: "easeOut" }}
      className="group flex flex-col overflow-hidden rounded-xl border border-[#E4E1D9] bg-white transition-colors hover:border-[#C8C4B8]"
    >
      <div className="relative aspect-video overflow-hidden bg-[#F5F4EF]">
        {thumb ? (
          <Image
            src={thumb}
            alt=""
            fill
            className={`object-cover transition-transform duration-500 group-hover:scale-[1.03] ${
              isEnded ? "grayscale-[40%] opacity-70" : ""
            }`}
            sizes="(max-width: 768px) 100vw, 33vw"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[#C8C4B8]">
            <FileQuestion size={28} strokeWidth={1.5} aria-hidden />
          </div>
        )}
        <div className="absolute left-3 top-3">
          <StatusBadge status={contest.status} />
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <div className="flex items-center justify-between">
          <TypeTag type={contest.type} />
          <span className="text-xs text-[#8A8677]">{formatDateUz(contest.start_time)}</span>
        </div>

        <h3 className="font-[var(--font-display)] text-[17px] leading-snug text-[#121212]">
          {contest.title}
        </h3>

        <div className="mt-auto flex items-center justify-between border-t border-[#EFEDE6] pt-3 text-xs text-[#8A8677]">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <FileQuestion size={14} strokeWidth={1.75} aria-hidden />
              {contest.questions_count} savol
            </span>
            <span className="flex items-center gap-1">
              <Users size={14} strokeWidth={1.75} aria-hidden />
              {pluralParticipants(contest.participants_count)}
            </span>
          </div>
          {contest.prizes.length > 0 && (
            <span className="flex items-center gap-1 text-[#B8892B]">
              <Award size={14} strokeWidth={1.75} aria-hidden />
              {contest.prizes.length}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-[#EFEDE6] px-4 py-3 text-sm font-medium text-[#121212]">
        {isEnded ? "Natijalarni ko'rish" : "Batafsil"}
        <ArrowUpRight
          size={16}
          strokeWidth={1.75}
          className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          aria-hidden
        />
      </div>
    </motion.a>
  );
}