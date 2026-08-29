import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCourseDetail, getTestInfo } from "@/lib/api/courses.server";
import { TestSessionView } from "@/components/courses/test-session-view";
import { AlertTriangle, Lock } from "lucide-react";

// Progress kabi bu sahifa ham hech qachon keshlanmasligi kerak —
// test natijalari va active_session_id doim eng so'nggi holat bo'lishi shart.
export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

type Props = { params: Promise<{ slug: string; testSlug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug, testSlug } = await params;
  const course = await getCourseDetail(slug);
  const modul = course?.modules.find((m) => m.test?.slug === testSlug);

  if (!modul?.test) return { title: "Test topilmadi | CFM" };
  return { title: `${modul.test.title} | CFM Testlar` };
}

function LockedState() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <Lock className="mb-4 size-12 text-white/20" />
      <h2 className="text-xl font-semibold text-white/80">Test hali qulflangan</h2>
      <p className="mt-1 text-sm text-white/40">
        Avval ushbu moduldagi barcha darslarni tugating
      </p>
    </div>
  );
}

function NotFoundState() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <AlertTriangle className="mb-4 size-12 text-amber-500/60" />
      <h2 className="text-xl font-semibold text-white/80">Test topilmadi</h2>
      <p className="mt-1 text-sm text-white/40">Iltimos, keyinroq qayta urinib ko'ring</p>
    </div>
  );
}

export default async function CourseTestPage({ params }: Props) {
  const { slug, testSlug } = await params;

  const course = await getCourseDetail(slug);
  if (!course) notFound();

  const modul = course.modules.find((m) => m.test?.slug === testSlug);
  if (!modul || !modul.test) notFound();

  const isLoggedIn = course.user_progress !== undefined;
  const isPaid = course.user_progress?.is_paid ?? false;
  const currentPrice = course.discount_price ?? course.price;
  const isFree = currentPrice <= 0;

  // course-curriculum.tsx bilan bir xil qulf logikasi — haqiqiy
  // lesson.user_status massividan hisoblanadi, keshlanadigan ms.cl
  // agregatidan emas.
  const isPaywallLocked = isLoggedIn && !isPaid && !isFree;
  const allLessonsDone =
    modul.total_lessons === 0 ||
    modul.lessons.every((l) => l.user_status?.is_completed ?? false);
  const isTestLocked = isPaywallLocked || modul.locked || !allLessonsDone;

  if (!isLoggedIn) {
    // Backend get_test_info login talab qiladi (get_current_user),
    // shuning uchun anonim userni bu yerda to'xtatamiz.
    return (
      <main className="min-h-screen bg-[#0a0a0a]">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <LockedState />
        </div>
      </main>
    );
  }

  if (isTestLocked) {
    return (
      <main className="min-h-screen bg-[#0a0a0a]">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <LockedState />
        </div>
      </main>
    );
  }

  const testInfo = await getTestInfo(modul.id);
  if (!testInfo) {
    return (
      <main className="min-h-screen bg-[#0a0a0a]">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <NotFoundState />
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0a0a0a]">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <TestSessionView modulId={modul.id} courseSlug={course.slug} testInfo={testInfo} />
      </div>
    </main>
  );
}