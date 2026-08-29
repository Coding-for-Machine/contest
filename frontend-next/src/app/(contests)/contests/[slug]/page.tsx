"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getContestBySlug } from "@/lib/contests/mock-data";
import { StatusBadge, TypeTag } from "@/components/contests/StatusBadge";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { PrizeList } from "@/components/contests/PrizeList";
import { Leaderboard } from "@/components/contests/Leaderboard";
import { JoinPanel } from "@/components/contests/JoinPanel";
import { ContestVideoPlayer } from "@/components/contests/ContestVideoPlayer";

export default function ContestDetailPage() {
  const params = useParams<{ slug: string }>();
  const contest = useMemo(() => getContestBySlug(params.slug), [params.slug]);

  if (!contest) {
    return (
      <main className="flex min-h-screen items-center justify-center text-[#8A8677]" >
        Musobaqa topilmadi.
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
        <a
          href="/contests"
          className="inline-flex items-center gap-1.5 text-sm text-[#8A8677] hover:text-[#121212]"
        >
          <ArrowLeft size={15} strokeWidth={1.75} aria-hidden />
          Barcha musobaqalar
        </a>

        <div className="mt-6 grid gap-10 lg:grid-cols-[1fr_300px]">
          {/* Main column */}
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <StatusBadge status={contest.status} />
              <TypeTag type={contest.type} />
            </div>

            <h1 className="mt-3 font-[var(--font-display)] text-3xl leading-tight text-[#121212] sm:text-[2.25rem]">
              {contest.title}
            </h1>

            <div className="mt-6">
              <ContestVideoPlayer video={contest.intro_video} title={contest.title} />
            </div>

            <section className="mt-8">
              <h2 className="font-[var(--font-display)] text-lg text-[#121212]">Tavsif</h2>
              <div className="mt-3">
                <MarkdownRenderer content={contest.description} />
              </div>
            </section>

            {contest.prizes.length > 0 && (
              <section className="mt-9">
                <h2 className="font-[var(--font-display)] text-lg text-[#121212]">Sovrinlar</h2>
                <div className="mt-3">
                  <PrizeList prizes={contest.prizes} />
                </div>
              </section>
            )}

            <section id="leaderboard" className="mt-9">
              <h2 className="font-[var(--font-display)] text-lg text-[#121212]">Reyting</h2>
              <div className="mt-3">
                <Leaderboard rows={contest.top_registrations ?? []} />
              </div>
            </section>
          </div>

          {/* Sidebar */}
          <div>
            <JoinPanel contest={contest} />
          </div>
        </div>
      </div>
    </main>
  );
}