"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/utils";
import type { ProblemSubmissionsResponse } from "@/lib/problems/types";
import { formatMemory, formatTime, formatDateTime } from "@/lib/problems/utils";
import {
  CheckCircle2,
  XCircle,
  Inbox,
  RotateCcw,
  AlertTriangle,
  ChevronRight,
  Code2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SubmissionDetailModal } from "./submission-detail-modal";

export function SubmissionList({ slug }: { slug: string }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data, isLoading, error, mutate } = useSWR<ProblemSubmissionsResponse>(
    `/api/problems/${slug}/submission?limit=10`,
    fetcher,
    { refreshInterval: 15000 }
  );

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 w-full animate-pulse rounded-xl bg-neutral-100"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-neutral-200 bg-white py-14 text-center">
        <AlertTriangle className="size-8 text-neutral-300" />
        <div>
          <p className="text-sm font-medium text-neutral-600">
            Taqdimotlarni yuklashda xatolik yuz berdi
          </p>
          <p className="mt-0.5 text-xs text-neutral-400">
            Internet aloqasini tekshirib, qayta urinib ko'ring
          </p>
        </div>
        <button
          onClick={() => mutate()}
          className="flex items-center gap-1.5 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100"
        >
          <RotateCcw className="size-3.5" />
          Qayta urinish
        </button>
      </div>
    );
  }

  if (!data || data.count === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-neutral-200 bg-white py-14 text-center">
        <Inbox className="size-8 text-neutral-300" />
        <p className="text-sm font-medium text-neutral-500">
          Hali hech qanday yechim yubormadingiz
        </p>
        <p className="text-xs text-neutral-400">
          Kodingizni yozib "Yuborish" tugmasini bosing — tarix shu yerda ko'rinadi
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      {/* Desktop header */}
      <div className="hidden grid-cols-12 gap-2 border-b border-neutral-100 bg-neutral-50 px-4 py-2 text-xs font-medium text-neutral-400 sm:grid">
        <span className="col-span-3">Holat</span>
        <span className="col-span-2">Til</span>
        <span className="col-span-2 text-center">Testlar</span>
        <span className="col-span-1 text-center">Vaqt</span>
        <span className="col-span-1 text-center">Xotira</span>
        <span className="col-span-3 text-right">Sana</span>
      </div>

      <ul className="divide-y divide-neutral-100">
        {data.data.map((sub) => (
          <SubmissionRow
            key={sub.id}
            sub={sub}
            onClick={() => setSelectedId(sub.id)}
          />
        ))}
      </ul>

      <SubmissionDetailModal
        submissionId={selectedId}
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}

function SubmissionRow({
  sub,
  onClick,
}: {
  sub: ProblemSubmissionsResponse["data"][0];
  onClick: () => void;
}) {
  const isAccepted = sub.status;

  return (
    <li
      onClick={onClick}
      className="group grid cursor-pointer grid-cols-2 items-center gap-2 px-4 py-3 text-sm transition-colors hover:bg-neutral-50 active:bg-neutral-100 sm:grid-cols-12"
    >
      <span className="col-span-2 flex items-center gap-2 sm:col-span-3">
        {isAccepted ? (
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1">
            <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
            <span className="text-xs font-semibold text-emerald-600">
              Accepted
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-1">
            <XCircle className="size-4 shrink-0 text-red-400" />
            <span className="text-xs font-semibold text-red-500">
              {sub.verdict || "Rad etildi"}
            </span>
          </div>
        )}
      </span>

      <span className="col-span-1 flex items-center gap-1.5 truncate font-medium text-neutral-700 sm:col-span-2">
        <Code2 className="size-3.5 text-neutral-400" />
        {sub.lang}
      </span>

      <span
        className={cn(
          "col-span-1 text-left sm:col-span-2 sm:text-center",
          sub.passed_count === sub.total_count
            ? "text-emerald-600"
            : "text-neutral-500"
        )}
      >
        <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs font-medium tabular-nums">
          {sub.passed_count}/{sub.total_count}
        </span>
      </span>

      <span className="col-span-1 hidden text-center tabular-nums text-neutral-500 sm:block">
        {formatTime(sub.time)}
      </span>

      <span className="col-span-1 hidden text-center tabular-nums text-neutral-500 sm:block">
        {formatMemory(sub.memory)}
      </span>

      <span className="col-span-2 flex items-center justify-end gap-2 text-right text-xs text-neutral-400 sm:col-span-3 sm:text-sm">
        <span className="tabular-nums">{formatDateTime(sub.created_at)}</span>
        <ChevronRight className="size-4 text-neutral-300 transition-colors group-hover:text-neutral-600" />
      </span>
    </li>
  );
}