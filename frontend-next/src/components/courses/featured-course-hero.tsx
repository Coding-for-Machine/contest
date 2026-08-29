"use client";

import Link from "next/link";
import Image from "next/image";
import { ArrowRight, PlayCircle, HelpCircle, Users, Play } from "lucide-react";
import type { CourseHeroData } from "@/lib/types/course";

interface FeaturedCourseHeroProps {
  hero: CourseHeroData;
}

export function FeaturedCourseHero({ hero }: FeaturedCourseHeroProps) {
  const price = Number(hero.price ?? 0);
  const discountPrice = hero.discount_price != null ? Number(hero.discount_price) : null;
  const currentPrice = discountPrice ?? price;
  const isFree = !currentPrice || currentPrice <= 0;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#121212]">
      {hero.video?.thumbnail && (
        <div className="absolute inset-0 opacity-[0.12]">
          <Image src={hero.video.thumbnail} alt="" fill className="object-cover" priority />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-r from-[#121212] via-[#121212]/90 to-transparent" />

      <div className="relative grid grid-cols-1 gap-8 px-8 py-10 sm:px-10 sm:py-12 lg:grid-cols-[1.1fr_auto] lg:items-center">
        <div className="flex flex-col gap-5">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 px-3 py-1 text-xs font-medium text-[#D9AE55]">
            <span className="size-1.5 rounded-full bg-[#D9AE55]" />
            Tavsiya etilgan kurs
          </span>

          <h2 className="font-display text-3xl font-bold leading-tight text-white sm:text-4xl">
            {hero.title}
          </h2>

          {hero.description && (
            <p className="max-w-lg text-sm leading-relaxed text-white/50">
              {hero.description.replace(/[#*`]/g, "").slice(0, 180)}
              {hero.description.length > 180 ? "..." : ""}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-white/40">
            <span className="flex items-center gap-2">
              <PlayCircle className="size-4 text-[#D9AE55]" />
              {hero.total_lessons} dars
            </span>
            <span className="flex items-center gap-2">
              <HelpCircle className="size-4 text-[#D9AE55]" />
              {hero.total_tests} test
            </span>
            {hero.students > 0 && (
              <span className="flex items-center gap-2">
                <Users className="size-4 text-[#D9AE55]" />
                {hero.students.toLocaleString()}+ o'quvchi
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={`/courses/${hero.slug}`}
              className="inline-flex items-center gap-2 rounded-lg bg-[#D9AE55] px-6 py-2.5 text-sm font-semibold text-[#121212] transition hover:opacity-90"
            >
              {isFree ? "Bepul boshlash" : "Kursni ko'rish"}
              <ArrowRight className="size-4" />
            </Link>
            <Link
              href={`/courses/${hero.slug}#curriculum`}
              className="rounded-lg border border-white/15 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-white/5"
            >
              Dastur bilan tanishish
            </Link>
          </div>
        </div>

        {hero.video?.thumbnail && (
          <div className="relative hidden aspect-[4/3] w-64 shrink-0 overflow-hidden rounded-xl border border-white/10 lg:block">
            <Image src={hero.video.thumbnail} alt={hero.title} fill className="object-cover" />
            <div className="absolute inset-0 flex items-center justify-center bg-black/20">
              <span className="flex size-12 items-center justify-center rounded-full bg-[#D9AE55]">
                <Play className="ml-0.5 size-5 fill-[#121212] text-[#121212]" />
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}