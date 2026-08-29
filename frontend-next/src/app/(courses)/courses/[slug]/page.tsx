import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { Suspense } from "react";
import { getCourseDetail } from "@/lib/api/courses.server";
import { getCourseAudience } from "@/lib/data/course-audiences";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { CourseHero } from "@/components/courses/course-hero";
import { CourseAudience } from "@/components/courses/course-audience";
import { CourseCurriculum } from "@/components/courses/course-curriculum";
import { CourseSidebar } from "@/components/courses/course-sidebar";
import { CourseFaq } from "@/components/courses/course-faq";
import { AlertTriangle, Loader2 } from "lucide-react";

// ─────────────────────────────────────────────────────────────
// MUHIM:
// Bu sahifa user-specific progress ko'rsatadi.
//
// Shuning uchun cache ishlatilmaydi:
// - Full Route Cache
// - Client Router Cache
// - fetch cache
// ─────────────────────────────────────────────────────────────
export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({
  params,
}: Props): Promise<Metadata> {
  const { slug } = await params;

  const course = await getCourseDetail(slug);

  if (!course) {
    return {
      title: "Kurs topilmadi | CFM",
    };
  }

  return {
    title: `${course.title} | CFM Kurslar`,
    description: course.description
      ?.replace(/[#*`]/g, "")
      .slice(0, 160),
  };
}

/* ==================== LOADING ==================== */

function LoadingState() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-white text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-[#C89B3C]/10">
        <Loader2 className="size-6 animate-spin text-[#A97920]" />
      </div>

      <div>
        <p className="text-sm font-semibold text-slate-700">
          Kurs yuklanmoqda...
        </p>

        <p className="mt-1 text-xs text-slate-400">
          Bir necha soniya kuting
        </p>
      </div>
    </div>
  );
}

/* ==================== ERROR ==================== */

function ErrorState() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center bg-white px-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-2xl bg-amber-50">
        <AlertTriangle className="size-8 text-amber-500" />
      </div>

      <h2 className="mt-5 text-xl font-bold text-slate-800">
        Kursni yuklashda xatolik
      </h2>

      <p className="mt-2 text-sm text-slate-400">
        Iltimos, keyinroq qayta urinib ko&apos;ring
      </p>
    </div>
  );
}

/* ==================== PAGE ==================== */

export default async function CourseDetailPage({
  params,
}: Props) {
  const { slug } = await params;

  let course;

  try {
    course = await getCourseDetail(slug);
  } catch (e) {
    return <ErrorState />;
  }

  if (!course) {
    notFound();
  }

  const audienceData = getCourseAudience(slug);
  const modules = course.modules || [];

  const isPaid = course.user_progress?.is_paid ?? false;
  const isLoggedIn = course.user_progress !== undefined;

  const firstLessonSlug =
    modules[0]?.lessons[0]?.slug;

  const currentPrice =
    course.discount_price ?? course.price;

  const isFree = currentPrice <= 0;

  return (
    <main className="min-h-screen bg-white">
      {/* ==================== HERO ==================== */}

      <Suspense fallback={<LoadingState />}>
        <CourseHero
          course={course}
          isPaid={isPaid}
          isLoggedIn={isLoggedIn}
          firstLessonSlug={firstLessonSlug}
          courseSlug={course.slug}
          progress={course.user_progress}
        />
      </Suspense>

      {/* ==================== CONTENT ==================== */}

      <div className="mx-auto max-w-7xl px-5 py-12 sm:px-6 sm:py-16 lg:px-8 lg:py-20">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-16 lg:items-start">
          {/* ==================== LEFT ==================== */}

          <div className="flex min-w-0 flex-col gap-14">
            {/* ==================== COURSE DESCRIPTION ==================== */}

            {course.description && (
              <section
                id="description"
                className="scroll-mt-24"
              >
                <div className="mb-6">
                  <h2 className="text-2xl font-bold tracking-tight text-slate-900">
                    Kurs haqida
                  </h2>

                  <div className="mt-3 h-1 w-10 rounded-full bg-[#C89B3C]" />
                </div>

                <div className="prose prose-slate max-w-none leading-7 text-slate-600 prose-headings:text-slate-900 prose-strong:text-slate-800 prose-a:text-[#A97920] prose-a:no-underline hover:prose-a:underline">
                  <MarkdownRenderer
                    content={course.description}
                  />
                </div>
              </section>
            )}

            {/* ==================== AUDIENCE ==================== */}

            {audienceData && (
              <Suspense fallback={<LoadingState />}>
                <CourseAudience data={audienceData} />
              </Suspense>
            )}

            {/* ==================== CURRICULUM ==================== */}

            <section
              id="curriculum"
              className="scroll-mt-24"
            >
              <div className="mb-6">
                <h2 className="text-2xl font-bold tracking-tight text-slate-900">
                  Kurs dasturi
                </h2>

                <div className="mt-3 h-1 w-10 rounded-full bg-[#C89B3C]" />
              </div>

              <CourseCurriculum
                modules={modules}
                courseSlug={course.slug}
                isPaid={isPaid}
                isLoggedIn={isLoggedIn}
                isFree={isFree}
              />
            </section>

            {/* ==================== FAQ ==================== */}

            <section
              id="faq"
              className="scroll-mt-24"
            >
              <div className="mb-6">
                <h2 className="text-2xl font-bold tracking-tight text-slate-900">
                  Ko&apos;p so&apos;raladigan savollar
                </h2>

                <div className="mt-3 h-1 w-10 rounded-full bg-[#C89B3C]" />
              </div>

              <CourseFaq />
            </section>
          </div>

          {/* ==================== SIDEBAR ==================== */}

          <aside className="lg:sticky lg:top-8">
            <CourseSidebar
              course={course}
              isPaid={isPaid}
              isLoggedIn={isLoggedIn}
            />
          </aside>
        </div>
      </div>
    </main>
  );
}