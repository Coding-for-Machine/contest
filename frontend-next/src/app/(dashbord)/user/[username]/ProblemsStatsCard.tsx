"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/utils";
import type { ProblemStats } from "@/lib/problems/types";

const RADIUS = 52;
const STROKE = 11;
const GAP_DEG = 4; // segmentlar orasidagi bo'shliq (gradus)
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const SIZE = (RADIUS + STROKE) * 2;

const DIFFICULTY_META = [
  { key: "easy" as const, label: "Oson", color: "#3DB87A" },
  { key: "medium" as const, label: "O'rta", color: "#D9AE55" },
  { key: "hard" as const, label: "Qiyin", color: "#D0645A" },
];

function buildSegments(stats: ProblemStats) {
  const gapLen = (GAP_DEG / 360) * CIRCUMFERENCE;
  const usable = CIRCUMFERENCE - gapLen * DIFFICULTY_META.length;
  let offset = 0;

  return DIFFICULTY_META.map((meta) => {
    const d = stats.by_difficulty[meta.key];
    // Segment uzunligi — shu daraja umumiy masalalar ichida qancha ulush
    // egallashiga proportsional (LeetCode uslubi)
    const trackLen = stats.total > 0 ? (d.total / stats.total) * usable : 0;
    // To'ldirilgan qism — shu daraja ichida nechta yechilganiga proportsional
    const fillLen = d.total > 0 ? (d.solved / d.total) * trackLen : 0;
    const seg = { ...meta, ...d, trackLen, fillLen, offset };
    offset += trackLen + gapLen;
    return seg;
  });
}

function StatsRingSkeleton() {
  return (
    <div className="rounded-2xl border border-[#ECEAE3] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="mb-4 h-4 w-28 rounded bg-[#F1EFE7] animate-pulse" />
      <div className="flex items-center gap-6">
        <div className="size-[126px] shrink-0 rounded-full bg-[#F1EFE7] animate-pulse" />
        <div className="flex-1 space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-3 w-full rounded bg-[#F1EFE7] animate-pulse" />
          ))}
        </div>
      </div>
    </div>
  );
}

export function ProblemsStatsCard() {
  const { data, isLoading } = useSWR<ProblemStats>("/api/problems/stats", fetcher, {
    dedupingInterval: 5 * 60_000,
    revalidateOnFocus: false,
  });

  if (isLoading) return <StatsRingSkeleton />;
  if (!data) return null;

  const segments = buildSegments(data);
  const c = RADIUS + STROKE;

  return (
    <div className="rounded-2xl border border-[#ECEAE3] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <h3 className="mb-4 text-sm font-semibold text-[#121212]">Mening holatim</h3>

      <div className="flex items-center gap-6">
        <div className="relative shrink-0" style={{ width: SIZE, height: SIZE }}>
          <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="-rotate-90">
            <circle cx={c} cy={c} r={RADIUS} fill="none" stroke="#F1EFE7" strokeWidth={STROKE} />
            {segments.map((seg) => (
              <g key={seg.key}>
                {/* Segment yo'lagi — xira rang, shu daraja necha % masalani tashkil qilishini bildiradi */}
                <circle
                  cx={c}
                  cy={c}
                  r={RADIUS}
                  fill="none"
                  stroke={seg.color}
                  strokeOpacity={0.16}
                  strokeWidth={STROKE}
                  strokeLinecap="round"
                  strokeDasharray={`${seg.trackLen} ${CIRCUMFERENCE - seg.trackLen}`}
                  strokeDashoffset={-seg.offset}
                />
                {/* To'ldirilgan qism — shu daraja ichida yechilgan ulush */}
                <circle
                  cx={c}
                  cy={c}
                  r={RADIUS}
                  fill="none"
                  stroke={seg.color}
                  strokeWidth={STROKE}
                  strokeLinecap="round"
                  strokeDasharray={`${seg.fillLen} ${CIRCUMFERENCE - seg.fillLen}`}
                  strokeDashoffset={-seg.offset}
                />
              </g>
            ))}
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold leading-none text-[#121212]">{data.solved}</span>
            <span className="mt-1 text-[11px] text-[#8C877D]">/ {data.total} yechilgan</span>
          </div>
        </div>

        <div className="flex-1 space-y-3">
          {segments.map((seg) => (
            <div key={seg.key} className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-[#706C63]">
                <span className="size-2 rounded-full" style={{ backgroundColor: seg.color }} />
                {seg.label}
              </span>
              <span className="font-medium text-[#121212]">
                {seg.solved}/{seg.total}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}