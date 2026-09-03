import Link from "next/link";
import { Award, CheckCircle2, ArrowRight, BookOpen } from "lucide-react";
import { getCourseDetail } from "@/lib/api/courses.server";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  const course = await getCourseDetail(slug);
  return {
    title: `${course?.title ?? "Kurs"} — Yakunlandi | CFM`,
  };
}

export default async function CourseCompletePage({ params }: Props) {
  const { slug } = await params;
  const course = await getCourseDetail(slug);

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-[#141414] border border-white/10 rounded-2xl p-8 text-center">
        <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-[#D9AE55]/20 text-[#D9AE55]">
          <Award className="size-8" />
        </div>

        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400 mb-4 border border-emerald-500/20">
          <CheckCircle2 className="size-3.5" />
          Muvaffaqiyatli yakunlandi
        </span>

        <h1 className="text-2xl font-bold text-white mb-2">
          Tabriklaymiz!
        </h1>
        <p className="text-sm text-neutral-400 mb-6">
          Siz <span className="font-semibold text-white">{course?.title || "kurs"}</span>ni to'liq tugatdingiz. O'zlashtirgan bilimlaringiz amaliyotda asqotishiga tilakdoshmiz!
        </p>

        <div className="flex flex-col gap-3">
          <Link
            href={`/courses/${slug}`}
            className="flex items-center justify-center gap-2 rounded-xl bg-[#D9AE55] px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-[#c49b45]"
          >
            <BookOpen className="size-4" />
            Kursga qaytish
          </Link>
          <Link
            href="/courses"
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/10"
          >
            Boshqa kurslar
            <ArrowRight className="size-4" />
          </Link>
        </div>
      </div>
    </main>
  );
}
