// app/problems/ProblemsListClient.tsx
"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import useSWRInfinite from "swr/infinite";
import Link from "next/link";
import { fetcher } from "@/lib/utils";
import type {
  ProblemsResponse,
  Problems,
  ProblemsSearchParams,
  Category,
  Tag,
} from "@/lib/problems/types";
import {
  CheckCircle2,
  Loader2,
  Search,
  X,
  Filter,
  ChevronDown,
  RotateCcw,
  SlidersHorizontal,
  AlertCircle,
} from "lucide-react";

interface Props {
  initialData: ProblemsResponse;
  searchParams: ProblemsSearchParams;
  categories: Category[];
  tags: Tag[];
  view: "filters" | "content";
}

const LIMIT = 20;

/* =================================================================
   SKELETON COMPONENTS
   ================================================================= */
function TableSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50/80">
            <tr>
              {Array.from({ length: 7 }).map((_, i) => (
                <th key={i} className="px-4 py-3">
                  <div className="h-3.5 w-16 animate-pulse rounded bg-slate-200" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {Array.from({ length: 10 }).map((_, idx) => (
              <tr key={idx}>
                <td className="px-4 py-3.5">
                  <div className="mx-auto size-5 animate-pulse rounded-full bg-slate-200" />
                </td>
                <td className="px-4 py-3.5">
                  <div className="h-4 w-48 animate-pulse rounded bg-slate-200" />
                </td>
                <td className="px-4 py-3.5">
                  <div className="h-4 w-20 animate-pulse rounded bg-slate-200" />
                </td>
                <td className="px-4 py-3.5">
                  <div className="h-5 w-14 animate-pulse rounded bg-slate-200" />
                </td>
                <td className="px-4 py-3.5">
                  <div className="ml-auto h-4 w-8 animate-pulse rounded bg-slate-200" />
                </td>
                <td className="px-4 py-3.5">
                  <div className="ml-auto h-4 w-10 animate-pulse rounded bg-slate-200" />
                </td>
                <td className="px-4 py-3.5">
                  <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilterSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
      <div className="h-9 w-full animate-pulse rounded-lg bg-slate-200" />
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 w-full animate-pulse rounded-lg bg-slate-200" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 w-full animate-pulse rounded-lg bg-slate-200" />
        ))}
      </div>
    </div>
  );
}

/* =================================================================
   MAIN COMPONENT
   ================================================================= */
export default function ProblemsListClient({
  initialData,
  searchParams: initialSP,
  categories,
  tags,
  view,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const urlSP = useSearchParams();

  // --- Filter State ---
  const [search, setSearch] = useState(initialSP.search || "");
  const [categoryId, setCategoryId] = useState(initialSP.category_id || "");
  const [tagId, setTagId] = useState(initialSP.tag_id || "");
  const [difficulty, setDifficulty] = useState(initialSP.difficulty || "");
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const activeFilterCount = useMemo(() => {
    let c = 0;
    if (search.trim()) c++;
    if (categoryId) c++;
    if (tagId) c++;
    if (difficulty) c++;
    return c;
  }, [search, categoryId, tagId, difficulty]);

  const hasActiveFilters = activeFilterCount > 0;

  // Build query string
  const buildQueryString = useCallback(() => {
    const p = new URLSearchParams();
    if (search.trim()) p.set("search", search.trim());
    if (categoryId) p.set("category_id", categoryId);
    if (tagId) p.set("tag_id", tagId);
    if (difficulty) p.set("difficulty", difficulty);
    return p.toString();
  }, [search, categoryId, tagId, difficulty]);

  // Auto-apply: text = debounced, others = instant
  useEffect(() => {
    const timer = setTimeout(() => {
      const qs = buildQueryString();
      router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    }, 300);
    return () => clearTimeout(timer);
  }, [search, buildQueryString, pathname, router]);

  useEffect(() => {
    const qs = buildQueryString();
    router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryId, tagId, difficulty]);

  const clearAll = () => {
    setSearch("");
    setCategoryId("");
    setTagId("");
    setDifficulty("");
    router.replace(pathname, { scroll: false });
  };

  // --- Data Fetching ---
  const filterKey = useMemo(() => buildQueryString(), [buildQueryString]);

  const getKey = (pageIndex: number, prev: ProblemsResponse | null) => {
    if (prev && prev.data.length === 0) return null;
    const p = new URLSearchParams(filterKey);
    p.set("limit", String(LIMIT));
    p.set("offset", String(pageIndex * LIMIT));
    return `/api/problems?${p.toString()}`;
  };

  const {
    data,
    error,
    isLoading, // true only on initial load
    isValidating, // true on any revalidation
    size,
    setSize,
    mutate,
  } = useSWRInfinite<ProblemsResponse>(getKey, fetcher, {
    fallbackData: [initialData],
    revalidateOnFocus: false,
    dedupingInterval: 60_000,
    keepPreviousData: true, // smooth transition between filters
  });

  const problems = useMemo(() => data?.flatMap((p) => p.data) ?? [], [data]);
  const totalCount = data?.[0]?.count ?? 0;
  const isEmpty = problems.length === 0;
  const hasMore = problems.length < totalCount;

  // Infinite scroll
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || isValidating) return;
    const obs = new IntersectionObserver(
      (entries) => entries[0].isIntersecting && setSize((s) => s + 1),
      { rootMargin: "600px" }
    );
    obs.observe(sentinelRef.current);
    return () => obs.disconnect();
  }, [hasMore, isValidating, setSize]);

  // Scroll to top on filter change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [filterKey]);

  // ==================== SIDEBAR FILTERS ====================
  if (view === "filters") {
    if (categories.length === 0 && tags.length === 0) {
      return <FilterSkeleton />;
    }

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <SlidersHorizontal className="size-4" strokeWidth={1.5} />
            Filterlar
          </div>
          {hasActiveFilters && (
            <button
              onClick={clearAll}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            >
              <RotateCcw className="size-3" />
              Tozalash
            </button>
          )}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 size-4 text-slate-400" strokeWidth={1.5} />
          <input
            type="text"
            placeholder="Qidirish..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-8 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-200"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
            >
              <X className="size-4" />
            </button>
          )}
        </div>

        {/* Difficulty */}
        <FilterSection title="Qiyinlik darajasi">
          <div className="space-y-1">
            {[
              { value: "easy", label: "Oson", dot: "bg-emerald-500" },
              { value: "medium", label: "O'rta", dot: "bg-amber-500" },
              { value: "hard", label: "Qiyin", dot: "bg-red-500" },
            ].map((d) => {
              const active = difficulty === d.value;
              return (
                <button
                  key={d.value}
                  onClick={() => setDifficulty(active ? "" : d.value)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                    active
                      ? "bg-slate-900 font-medium text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <span className={`size-2 rounded-full ${active ? "bg-white" : d.dot}`} />
                  {d.label}
                  {active && <CheckCircle2 className="ml-auto size-4" strokeWidth={1.5} />}
                </button>
              );
            })}
          </div>
        </FilterSection>

        {/* Category */}
        <FilterSection title="Kategoriya">
          <div className="max-h-56 space-y-0.5 overflow-y-auto pr-1 scrollbar-thin">
            {categories.map((c) => {
              const active = categoryId === String(c.id);
              return (
                <button
                  key={c.id}
                  onClick={() => setCategoryId(active ? "" : String(c.id))}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                    active
                      ? "bg-slate-900 font-medium text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <span className="truncate">{c.name}</span>
                  {active && <CheckCircle2 className="ml-auto size-4 shrink-0" strokeWidth={1.5} />}
                </button>
              );
            })}
          </div>
        </FilterSection>

        {/* Tags */}
        <FilterSection title="Teglar">
          <div className="flex flex-wrap gap-2">
            {tags.map((t) => {
              const active = tagId === String(t.id);
              return (
                <button
                  key={t.id}
                  onClick={() => setTagId(active ? "" : String(t.id))}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                    active
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-slate-200 text-slate-600 hover:border-slate-400 hover:text-slate-900"
                  }`}
                >
                  {t.name}
                </button>
              );
            })}
          </div>
        </FilterSection>
      </div>
    );
  }

  // ==================== CONTENT (TABLE) ====================
  return (
    <div className="space-y-4">
      {/* Mobile Filter Toggle */}
      <div className="lg:hidden">
        <button
          onClick={() => setMobileFiltersOpen((v) => !v)}
          className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm"
        >
          <span className="flex items-center gap-2">
            <Filter className="size-4" strokeWidth={1.5} />
            Filterlar
            {activeFilterCount > 0 && (
              <span className="rounded-full bg-slate-900 px-1.5 py-0.5 text-[10px] text-white">
                {activeFilterCount}
              </span>
            )}
          </span>
          <ChevronDown
            className={`size-4 text-slate-400 transition-transform ${mobileFiltersOpen ? "rotate-180" : ""}`}
          />
        </button>

        {mobileFiltersOpen && (
          <div className="mt-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <MobileFilters
              search={search}
              setSearch={setSearch}
              difficulty={difficulty}
              setDifficulty={setDifficulty}
              categoryId={categoryId}
              setCategoryId={setCategoryId}
              tagId={tagId}
              setTagId={setTagId}
              categories={categories}
              tags={tags}
              clearAll={clearAll}
            />
          </div>
        )}
      </div>

      {/* Active Filter Pills */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2">
          {search && <FilterPill label={`"${search}"`} onRemove={() => setSearch("")} />}
          {difficulty && (
            <FilterPill
              label={difficulty === "easy" ? "Oson" : difficulty === "medium" ? "O'rta" : "Qiyin"}
              onRemove={() => setDifficulty("")}
            />
          )}
          {categoryId && (
            <FilterPill
              label={categories.find((c) => String(c.id) === categoryId)?.name ?? ""}
              onRemove={() => setCategoryId("")}
            />
          )}
          {tagId && (
            <FilterPill
              label={tags.find((t) => String(t.id) === tagId)?.name ?? ""}
              onRemove={() => setTagId("")}
            />
          )}
          <button
            onClick={clearAll}
            className="text-xs font-medium text-slate-500 underline-offset-2 hover:text-slate-900 hover:underline"
          >
            Hammasini tozalash
          </button>
        </div>
      )}

      {/* Results count */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          {isLoading ? (
            <span className="inline-flex items-center gap-1">
              <Loader2 className="size-3 animate-spin" />
              Yuklanmoqda...
            </span>
          ) : (
            <>
              <span className="font-medium text-slate-900">{totalCount}</span> ta masala
            </>
          )}
        </span>
      </div>

      {/* Table or Skeleton */}
      {isLoading && !data ? (
        <TableSkeleton />
      ) : error ? (
        <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-10 text-center">
          <AlertCircle className="mx-auto mb-2 size-6 text-red-400" />
          <p className="text-sm font-medium text-red-600">Yuklashda xatolik</p>
          <button
            onClick={() => mutate()}
            className="mt-2 text-xs text-red-500 underline hover:text-red-700"
          >
            Qayta urinish
          </button>
        </div>
      ) : isEmpty && !isValidating ? (
        <div className="rounded-xl border border-dashed border-slate-200 py-16 text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-slate-50">
            <Search className="size-5 text-slate-300" strokeWidth={1.5} />
          </div>
          <p className="mt-3 text-sm font-medium text-slate-900">Masalalar topilmadi</p>
          <p className="mt-1 text-xs text-slate-500">Boshqa filterlarni sinab ko'ring</p>
          <button
            onClick={clearAll}
            className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800"
          >
            Filterlarni tozalash
          </button>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-100 bg-slate-50/80 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="w-14 px-4 py-3 text-center">Holat</th>
                    <th className="min-w-[280px] px-4 py-3">Nomi</th>
                    <th className="px-4 py-3">Kategoriya</th>
                    <th className="px-4 py-3">Qiyinlik</th>
                    <th className="px-4 py-3 text-right">XP</th>
                    <th className="px-4 py-3 text-right">Qabul</th>
                    <th className="hidden px-4 py-3 xl:table-cell">Teglar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {problems.map((p, idx) => (
                    <ProblemRow key={`${p.id}-${idx}`} problem={p} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Sentinel / Loading */}
            <div ref={sentinelRef} className="border-t border-slate-100 py-4 text-center">
              {hasMore ? (
                <Loader2 className="mx-auto size-5 animate-spin text-slate-400" />
              ) : problems.length > 0 ? (
                <span className="text-xs text-slate-400">Barchasi yuklandi</span>
              ) : null}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* =================================================================
   SUB-COMPONENTS
   ================================================================= */
function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-slate-100 pt-5">
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </h4>
      {children}
    </div>
  );
}

function FilterPill({ label, onRemove }: { label: string; onRemove: () => void }) {
  if (!label) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm">
      {label}
      <button
        onClick={onRemove}
        className="ml-0.5 rounded-full p-0.5 transition hover:bg-slate-100"
      >
        <X className="size-3 text-slate-400" />
      </button>
    </span>
  );
}

function ProblemRow({ problem }: { problem: Problems }) {
  return (
    <tr className="group transition-colors hover:bg-slate-50/60">
      <td className="px-4 py-3.5 text-center">
        {problem.solved ? (
          <CheckCircle2 className="mx-auto size-5 text-emerald-600" strokeWidth={1.5} />
        ) : (
          <span className="mx-auto block size-4 rounded-full border-2 border-slate-200 transition group-hover:border-slate-300" />
        )}
      </td>
      <td className="px-4 py-3.5">
        <Link
          href={`/problem/${problem.slug}`}
          className="font-medium text-slate-900 hover:text-slate-600 hover:underline"
        >
          {problem.title}
        </Link>
      </td>
      <td className="px-4 py-3.5 text-slate-500">{problem.category || "—"}</td>
      <td className="px-4 py-3.5">
        <DifficultyBadge difficulty={problem.difficulty} />
      </td>
      <td className="px-4 py-3.5 text-right font-medium tabular-nums text-slate-700">
        {problem.xp}
      </td>
      <td className="px-4 py-3.5 text-right tabular-nums text-slate-500">
        {typeof problem.acceptance === "number" ? `${problem.acceptance}%` : "—"}
      </td>
      <td className="hidden px-4 py-3.5 xl:table-cell">
        <div className="flex flex-wrap gap-1.5">
          {problem.tags?.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[11px] text-slate-600"
            >
              {tag}
            </span>
          ))}
          {problem.tags && problem.tags.length > 3 && (
            <span className="text-[11px] text-slate-400">+{problem.tags.length - 3}</span>
          )}
        </div>
      </td>
    </tr>
  );
}

function DifficultyBadge({ difficulty }: { difficulty: Problems["difficulty"] }) {
  const map = {
    easy: { cls: "text-emerald-700 bg-emerald-50 border-emerald-200", lbl: "Oson" },
    medium: { cls: "text-amber-700 bg-amber-50 border-amber-200", lbl: "O'rta" },
    hard: { cls: "text-red-700 bg-red-50 border-red-200", lbl: "Qiyin" },
  };
  const d = map[difficulty] ?? { cls: "text-slate-600 bg-slate-50 border-slate-200", lbl: difficulty };
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${d.cls}`}>
      {d.lbl}
    </span>
  );
}

function MobileFilters({
  search,
  setSearch,
  difficulty,
  setDifficulty,
  categoryId,
  setCategoryId,
  tagId,
  setTagId,
  categories,
  tags,
  clearAll,
}: {
  search: string;
  setSearch: (v: string) => void;
  difficulty: string;
  setDifficulty: (v: string) => void;
  categoryId: string;
  setCategoryId: (v: string) => void;
  tagId: string;
  setTagId: (v: string) => void;
  categories: Category[];
  tags: Tag[];
  clearAll: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-900">Filterlar</span>
        <button onClick={clearAll} className="text-xs text-slate-500 hover:text-slate-900">
          Tozalash
        </button>
      </div>

      <input
        type="text"
        placeholder="Qidirish..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm focus:border-slate-400 focus:outline-none"
      />

      <div>
        <p className="mb-2 text-xs font-semibold text-slate-500">Qiyinlik</p>
        <div className="flex gap-2">
          {["easy", "medium", "hard"].map((d) => (
            <button
              key={d}
              onClick={() => setDifficulty(difficulty === d ? "" : d)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                difficulty === d ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {d === "easy" ? "Oson" : d === "medium" ? "O'rta" : "Qiyin"}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold text-slate-500">Kategoriya</p>
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
        >
          <option value="">Barchasi</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold text-slate-500">Teg</p>
        <select
          value={tagId}
          onChange={(e) => setTagId(e.target.value)}
          className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm"
        >
          <option value="">Barchasi</option>
          {tags.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}