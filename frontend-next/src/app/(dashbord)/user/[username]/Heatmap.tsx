"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { ChevronDown, Flame } from "lucide-react";
import { fetcher } from "@/lib/utils";

interface HeatmapResponse {
  telegram_id: number;
  year: number;
  start_date: string;
  end_date: string;
  total_tasks: number;
  total_active_days: number;
  current_streak: number;
  max_streak: number;
  heatmap: Record<string, number>;
}

interface Day {
  date: string;
  count: number;
  month: number;
  isOutsideYear: boolean;
}

interface Week {
  days: Day[];
  month: number;
  monthChanged: boolean;
}

const DAY_SIZE = 13;
const GAP = 4;

const MONTHS = [
  "Yanvar",
  "Fevral",
  "Mart",
  "Aprel",
  "May",
  "Iyun",
  "Iyul",
  "Avgust",
  "Sentabr",
  "Oktabr",
  "Noyabr",
  "Dekabr",
];

const WEEK_DAYS = [
  "",
  "Du",
  "",
  "Chor",
  "",
  "Jum",
  "",
];

const INTENSITIES = [
  "bg-[#F3F1EB] border-[#E7E3D8]",
  "bg-[#F3DFAF] border-[#E8CE92]",
  "bg-[#E8C77E] border-[#DCB665]",
  "bg-[#D69F46] border-[#C89037]",
  "bg-[#AA7127] border-[#985F1D]",
];

function dateKey(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");

  return `${y}-${m}-${d}`;
}

function parseDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);

  return new Date(year, month - 1, day);
}

function formatDate(value: string) {
  return parseDate(value).toLocaleDateString("uz-UZ", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function getIntensity(count: number) {
  if (count <= 0) return INTENSITIES[0];
  if (count <= 2) return INTENSITIES[1];
  if (count <= 5) return INTENSITIES[2];
  if (count <= 8) return INTENSITIES[3];

  return INTENSITIES[4];
}

/**
 * Tanlangan yil uchun GitHub/LeetCode uslubidagi calendar.
 *
 * Muhim:
 * - Hafta Dushanbadan boshlanadi.
 * - Joriy yil: bugungi kun eng oxirgi real kun.
 * - O'tgan yil: 31-dekabr eng oxirgi kun.
 * - Kalendar chap tomondan boshlanishi uchun kerakli bo'sh
 *   kunlar qo'shiladi.
 */
function buildCalendar(
  year: number,
  heatmap: Record<string, number>
): Week[] {
  const today = new Date();

  const yearStart = new Date(year, 0, 1);
  const yearEnd =
    year === today.getFullYear()
      ? today
      : new Date(year, 11, 31);

  // JS:
  // Sunday = 0
  // Monday = 1
  const startDay = yearStart.getDay();

  // Monday-based offset
  const startOffset = startDay === 0 ? 6 : startDay - 1;

  const calendarStart = new Date(yearStart);
  calendarStart.setDate(calendarStart.getDate() - startOffset);

  const endDay = yearEnd.getDay();

  const endOffset = endDay === 0 ? 0 : 7 - endDay;

  const calendarEnd = new Date(yearEnd);
  calendarEnd.setDate(calendarEnd.getDate() + endOffset);

  const totalDays =
    Math.floor(
      (calendarEnd.getTime() - calendarStart.getTime()) /
        86400000
    ) + 1;

  const totalWeeks = Math.ceil(totalDays / 7);

  const weeks: Week[] = [];

  let previousMonth = -1;

  for (let weekIndex = 0; weekIndex < totalWeeks; weekIndex++) {
    const days: Day[] = [];

    for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
      const date = new Date(calendarStart);

      date.setDate(
        calendarStart.getDate() +
          weekIndex * 7 +
          dayIndex
      );

      const key = dateKey(date);
      const month = date.getMonth();

      const isOutsideYear =
        date.getFullYear() !== year ||
        date > yearEnd;

      days.push({
        date: key,
        count: heatmap[key] ?? 0,
        month,
        isOutsideYear,
      });
    }

    /**
     * Haftaning asosiy oyi:
     * real yil ichidagi birinchi kunning oyi.
     */
    const firstRealDay =
      days.find((day) => !day.isOutsideYear) ?? days[0];

    const month = firstRealDay.month;

    weeks.push({
      days,
      month,
      monthChanged: month !== previousMonth,
    });

    previousMonth = month;
  }

  return weeks;
}

/**
 * Oy nomining grid ichidagi pozitsiyasi.
 *
 * Separator aynan yangi oy boshlangan haftaning chap tomoniga
 * qo'yiladi.
 */
function getMonthLabel(week: Week) {
  if (!week.monthChanged) return "";

  return MONTHS[week.month];
}

function HeatmapSkeleton() {
  return (
    <section className="overflow-hidden rounded-2xl border border-[#E9E6DD] bg-white shadow-sm">
      <div className="border-b border-[#F0EEE8] px-5 py-4">
        <div className="h-4 w-32 animate-pulse rounded bg-[#F1EFE7]" />
        <div className="mt-2 h-3 w-48 animate-pulse rounded bg-[#F1EFE7]" />
      </div>

      <div className="overflow-x-auto p-5">
        <div className="min-w-[720px]">
          <div className="mb-3 ml-8 h-3 w-full animate-pulse rounded bg-[#F1EFE7]" />

          <div className="flex gap-1">
            <div className="flex w-7 shrink-0 flex-col justify-between">
              {WEEK_DAYS.map((_, i) => (
                <div
                  key={i}
                  className="h-[13px] w-5 animate-pulse rounded bg-[#F1EFE7]"
                />
              ))}
            </div>

            <div className="flex gap-1">
              {Array.from({ length: 53 }).map((_, w) => (
                <div
                  key={w}
                  className="flex flex-col gap-1"
                >
                  {Array.from({ length: 7 }).map((_, d) => (
                    <div
                      key={d}
                      className="size-[13px] animate-pulse rounded-[3px] bg-[#F1EFE7]"
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Heatmap({
  telegramId,
}: {
  telegramId: number;
}) {
  const currentYear = new Date().getFullYear();

  const [year, setYear] = useState(currentYear);

  const availableYears = useMemo(
    () =>
      Array.from(
        { length: 5 },
        (_, index) => currentYear - index
      ),
    [currentYear]
  );

  const { data, isLoading } = useSWR<HeatmapResponse>(
    `/api/user/heatmap/${telegramId}?year=${year}`,
    fetcher,
    {
      keepPreviousData: true,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 5 * 60 * 1000,
    }
  );

  const weeks = useMemo(() => {
    if (!data) return [];

    return buildCalendar(year, data.heatmap);
  }, [year, data]);

  if (isLoading && !data) {
    return <HeatmapSkeleton />;
  }

  if (!data) {
    return null;
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-[#E9E6DD] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      {/* =====================================================
          HEADER
      ====================================================== */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#F0EEE8] px-5 py-4">
        <div>
          <h3 className="text-[15px] font-semibold tracking-tight text-[#181818]">
            Faollik
          </h3>

          <p className="mt-0.5 text-xs text-[#8B877E]">
            {data.total_tasks.toLocaleString("uz-UZ")} ta
            topshiriq · {data.total_active_days} faol kun
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* STREAK */}
          <div className="flex items-center gap-1.5 rounded-lg border border-orange-100 bg-orange-50 px-2.5 py-1.5 text-xs font-medium text-orange-600">
            <Flame className="size-3.5 fill-current" />

            <span>
              {data.current_streak} kun
            </span>

            <span className="text-orange-300">
              /
            </span>

            <span>
              {data.max_streak}
            </span>
          </div>

          {/* YEAR SELECT */}
          <div className="relative">
            <select
              value={year}
              onChange={(e) =>
                setYear(Number(e.target.value))
              }
              className="
                cursor-pointer appearance-none
                rounded-lg border border-[#E1DEC9]
                bg-[#FAF9F6]
                py-1.5 pl-3 pr-8
                text-xs font-medium text-[#555149]
                outline-none
                transition
                hover:bg-[#F4F2EC]
                focus:border-[#C9B77C]
                focus:ring-2 focus:ring-[#EADDB6]/60
              "
              aria-label="Yilni tanlash"
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>

            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-[#777168]" />
          </div>
        </div>
      </div>

      {/* =====================================================
          HEATMAP
      ====================================================== */}
      <div className="overflow-x-auto px-5 py-5">
        <div className="min-w-[720px]">
          {/* MONTH LABELS */}
          <div className="mb-2 flex pl-8">
            <div className="flex gap-1">
              {weeks.map((week, index) => {
                const label = getMonthLabel(week);

                return (
                  <div
                    key={index}
                    className={`
                      relative h-4 w-[13px] shrink-0
                      text-[10px] font-medium
                      leading-4 text-[#918B81]
                      ${
                        week.monthChanged
                          ? "border-l border-[#DCD7CA] pl-1"
                          : ""
                      }
                    `}
                  >
                    {label}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex">
            {/* WEEKDAY LABELS */}
            <div className="mr-2 flex w-6 shrink-0 flex-col gap-1">
              {WEEK_DAYS.map((day, index) => (
                <div
                  key={index}
                  className="flex h-[13px] items-center text-[9px] leading-none text-[#9B958A]"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* GRID */}
            <div className="flex gap-1">
              {weeks.map((week, weekIndex) => (
                <div
                  key={weekIndex}
                  className={`
                    relative flex flex-col gap-1
                    ${
                      week.monthChanged && weekIndex !== 0
                        ? "border-l border-[#DDD8CC] pl-1"
                        : ""
                    }
                  `}
                >
                  {week.days.map((day) => {
                    const inactive = day.isOutsideYear;

                    return (
                      <div
                        key={day.date}
                        className="group relative"
                      >
                        <div
                          className={`
                            size-[13px]
                            rounded-[3px]
                            border
                            transition-all
                            duration-100
                            ${
                              inactive
                                ? "border-transparent bg-transparent"
                                : getIntensity(day.count)
                            }
                            ${
                              !inactive
                                ? "group-hover:z-20 group-hover:scale-[1.45] group-hover:border-black/20 group-hover:shadow-md"
                                : ""
                            }
                          `}
                        />

                        {/* TOOLTIP */}
                        {!inactive && (
                          <div
                            className="
                              pointer-events-none
                              absolute bottom-full left-1/2
                              z-50 mb-2
                              hidden -translate-x-1/2
                              whitespace-nowrap
                              rounded-md
                              bg-[#161616]
                              px-2.5 py-1.5
                              text-[11px]
                              text-white
                              shadow-xl
                              group-hover:block
                            "
                          >
                            <div className="font-medium">
                              {day.count === 0
                                ? "Faollik yo‘q"
                                : `${day.count} ta topshiriq`}
                            </div>

                            <div className="mt-0.5 text-[10px] text-neutral-400">
                              {formatDate(day.date)}
                            </div>

                            <div
                              className="
                                absolute left-1/2 top-full
                                -translate-x-1/2
                                border-[4px]
                                border-transparent
                                border-t-[#161616]
                              "
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* =================================================
              LEGEND
          ================================================== */}
          <div className="mt-5 flex items-center justify-end gap-1.5 text-[10px] text-[#918B81]">
            <span className="mr-0.5">
              Kam
            </span>

            {INTENSITIES.map((cls, index) => (
              <span
                key={index}
                className={`size-[11px] rounded-[2px] border ${cls}`}
              />
            ))}

            <span className="ml-0.5">
              Ko‘p
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}