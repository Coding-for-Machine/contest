"use client";

import Link from "next/link";
import Image from "next/image";
import { Lock, CheckCircle2, PlayCircle, FileQuestion, ArrowRight } from "lucide-react";

interface CourseCardProps {
  course: {
    id: number;
    title: string;
    slug: string;
    price: number;
    discount_price?: number | null;
    thumbnail?: string | null;
    total_lessons: number;
    total_tests: number;
    is_paid?: boolean;
    is_completed?: boolean;
    students?: number;
  };
}

export function CourseCard({ course }: CourseCardProps) {
  const price = Number(course.price ?? 0);
  const discountPrice = course.discount_price !== null && course.discount_price !== undefined
    ? Number(course.discount_price)
    : null;
  const currentPrice = discountPrice ?? price;
  const hasDiscount = discountPrice !== null && discountPrice < price;
  const isFree = !currentPrice || currentPrice <= 0;

  return (
    <Link
      href={`/courses/${course.slug}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-white/10 bg-[#121212] transition-all duration-300 hover:border-[#D9AE55]/40 hover:bg-[#161616]"
    >
      {/* Thumbnail */}
      <div className="relative aspect-[16/9] overflow-hidden bg-neutral-900">
        {course.thumbnail ? (
          <Image
            src={course.thumbnail}
            alt={course.title}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <PlayCircle className="size-10 text-white/20" />
          </div>
        )}

        {/* Badges */}
        <div className="absolute left-3 top-3 flex gap-2">
          {course.is_completed && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/90 px-2.5 py-1 text-[11px] font-medium text-white backdrop-blur">
              <CheckCircle2 className="size-3" />
              Tugallangan
            </span>
          )}
          {!course.is_paid && !isFree && (
            <span className="inline-flex items-center gap-1 rounded-full bg-black/60 px-2.5 py-1 text-[11px] font-medium text-white/90 backdrop-blur ring-1 ring-white/10">
              <Lock className="size-3" />
              Pullik
            </span>
          )}
          {isFree && (
            <span className="rounded-full bg-[#D9AE55] px-2.5 py-1 text-[11px] font-medium text-[#121212]">
              Bepul
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 flex-col p-5">
        <h3 className="font-display text-lg font-bold leading-snug text-white transition-colors group-hover:text-[#D9AE55]">
          {course.title}
        </h3>

        <div className="mt-3 flex items-center gap-4 text-xs text-white/40">
          <span className="flex items-center gap-1.5">
            <PlayCircle className="size-3.5" />
            {course.total_lessons} dars
          </span>
          <span className="flex items-center gap-1.5">
            <FileQuestion className="size-3.5" />
            {course.total_tests} test
          </span>
        </div>

        <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-4">
          <div className="flex items-baseline gap-2">
            {isFree ? (
              <span className="text-sm font-semibold text-[#D9AE55]">Bepul</span>
            ) : (
              <>
                {hasDiscount && (
                  <span className="text-xs text-white/30 line-through">
                    {price.toLocaleString()}
                  </span>
                )}
                <span className="text-sm font-semibold text-white">
                  {currentPrice.toLocaleString()} so'm
                </span>
              </>
            )}
          </div>

          <span className="flex items-center gap-1 text-xs text-[#D9AE55] opacity-0 transition-opacity group-hover:opacity-100">
            Ko'rish
            <ArrowRight className="size-3" />
          </span>
        </div>
      </div>
    </Link>
  );
}