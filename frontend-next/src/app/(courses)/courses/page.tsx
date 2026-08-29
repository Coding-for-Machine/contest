import type { Metadata } from "next";
import { Suspense } from "react";
import { getCourseList, getHeroCourse } from "@/lib/api/courses.server";
import { GraduationCap, AlertTriangle, Loader2 } from "lucide-react";
import { CourseListGrid } from "@/components/courses/course-list-grid";
import { FeaturedCourseHero } from "@/components/courses/featured-course-hero";

export const metadata: Metadata = {
  title: "Kurslar | CFM",
  description: "Professional onlayn kurslar",
};

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-80 animate-pulse rounded-xl bg-[#1a1a1a]" />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <GraduationCap className="mb-4 size-12 text-white/20" />
      <h3 className="text-lg font-semibold text-white/80">Hozircha kurslar mavjud emas</h3>
      <p className="mt-1 text-sm text-white/40">Tez orada yangi kurslar qo'shiladi</p>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <AlertTriangle className="mb-4 size-12 text-amber-500/60" />
      <h3 className="text-lg font-semibold text-white/80">Ma'lumotlarni yuklashda xatolik</h3>
      <p className="mt-1 text-sm text-white/40">Iltimos, sahifani qayta yuklang</p>
    </div>
  );
}

export default async function CoursesPage() {
  let courses: Awaited<ReturnType<typeof getCourseList>> = [];
  let hero: Awaited<ReturnType<typeof getHeroCourse>> = null;
  let hasError = false;

  try {
    [courses, hero] = await Promise.all([
      getCourseList(),
      getHeroCourse(),
    ]);
  } catch (e) {
    console.error("Courses page error:", e);
    hasError = true;
  }

  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto max-w-7xl px-6 pt-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Kurslar
        </h1>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
        {hasError ? (
          <ErrorState />
        ) : (
          <>
            {hero && (
              <div className="mb-12">
                <FeaturedCourseHero hero={hero} />
              </div>
            )}

            {courses.length === 0 ? (
              <EmptyState />
            ) : (
              <Suspense fallback={<SkeletonGrid />}>
                <CourseListGrid courses={courses} />
              </Suspense>
            )}
          </>
        )}
      </div>
    </main>
  );
}