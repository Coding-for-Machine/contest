// components/ProblemsStatsWidget.tsx
"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/utils";
import type { ProblemStats } from "@/lib/problems/types";

const DIFFICULTY_LABELS: Record<"easy" | "medium" | "hard", string> = {
  easy: "Oson",
  medium: "O'rta",
  hard: "Qiyin",
};

export default function ProblemsStatsWidget() {
  const { data, error, isLoading } = useSWR<ProblemStats>("/api/problems/stats", fetcher);

  if (isLoading) {
    return <div className="h-24 w-full animate-pulse rounded-2xl bg-neutral-100" />;
  }

  // Backend ulanmagan yoki boshqa xato bo'lsa — butun sahifani buzmasdan,
  // shunchaki bu vidjetni jimgina yashiramiz (statistika ikkinchi darajali
  // ma'lumot, sahifaning asosiy funksiyasi emas)
  if (error || !data) return null;

  const percent = data.total > 0 ? Math.round((data.solved / data.total) * 100) : 0;

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-900">Mening holatim</h3>
        <span className="text-sm text-neutral-500">
          {data.solved} / {data.total} yechilgan
        </span>
      </div>

      <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
        <div
          className="h-full rounded-full bg-orange-500 transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-3 text-center text-xs">
        {(["easy", "medium", "hard"] as const).map((d) => {
          const item = data.by_difficulty[d];
          if (!item) return null;
          return (
            <div key={d} className="rounded-xl bg-neutral-50 py-2">
              <p className="font-semibold text-neutral-900">
                {item.solved}/{item.total}
              </p>
              <p className="text-neutral-500">{DIFFICULTY_LABELS[d]}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}