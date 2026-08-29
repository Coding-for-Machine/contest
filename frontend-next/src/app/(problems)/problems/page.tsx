// app/problems/page.tsx
"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import useSWR from "swr";
import useSWRInfinite from "swr/infinite";
import Link from "next/link";
import { motion } from "framer-motion";
import { fetcher } from "@/lib/utils";
import type { ProblemsResponse, Problems, Category, Tag } from "@/lib/problems/types";
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
  Target,
  Hash,
  Terminal,
} from "lucide-react";

const LIMIT = 20;

/* ================================================================
   TYPES
   ================================================================ */
interface StatsData {
  total: number;
  solved: number;
  by_difficulty: Record<string, { total: number; solved: number }>;
}

/* ================================================================
   SKELETON COMPONENTS (light theme)
   ================================================================ */
function TableSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50/60">
            <tr>
              {Array.from({ length: 8 }).map((_, i) => (
                <th key={i} className="px-4 py-3">
                  <div className="h-3.5 w-16 animate-pulse rounded bg-slate-200" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {Array.from({ length: 10 }).map((_, idx) => (
              <tr key={idx}>
                <td className="px-2 py-3.5">
                  <span className="block w-8 text-right font-mono text-xs text-slate-300">
                    {(idx + 1).toString().padStart(2, "0")}
                  </span>
                </td>
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

function SidebarSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
      <div className="h-9 w-full animate-pulse rounded-lg bg-slate-200" />
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-9 w-full animate-pulse rounded-lg bg-slate-200" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-9 w-full animate-pulse rounded-lg bg-slate-200" />
        ))}
      </div>
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-2 h-4 w-20 animate-pulse rounded bg-slate-200" />
          <div className="h-8 w-12 animate-pulse rounded bg-slate-200" />
        </div>
      ))}
    </div>
  );
}

/* ================================================================
   WINDOW CHROME
   ================================================================ */
function WindowChrome({ className }: { className?: string }) {
  return (
    <div className={`flex items-center gap-1.5 ${className ?? ""}`}>
      <span className="h-2.5 w-2.5 rounded-full bg-white/40" />
      <span className="h-2.5 w-2.5 rounded-full bg-white/30" />
      <span className="h-2.5 w-2.5 rounded-full bg-white/20" />
    </div>
  );
}

/* ================================================================
   MAIN PAGE
   ================================================================ */
export default function ProblemsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const urlParams = useSearchParams();

  // --- Filter State ---
  const [search, setSearch] = useState(urlParams.get("search") || "");
  const [categoryId, setCategoryId] = useState(urlParams.get("category_id") || "");
  const [tagId, setTagId] = useState(urlParams.get("tag_id") || "");
  const [difficulty, setDifficulty] = useState(urlParams.get("difficulty") || "");
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const [debouncedSearch, setDebouncedSearch] = useState(search);
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    const p = new URLSearchParams();
    if (debouncedSearch.trim()) p.set("search", debouncedSearch.trim());
    if (categoryId) p.set("category_id", categoryId);
    if (tagId) p.set("tag_id", tagId);
    if (difficulty) p.set("difficulty", difficulty);
    const qs = p.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, categoryId, tagId, difficulty]);

  const activeFilterCount = useMemo(() => {
    let c = 0;
    if (debouncedSearch.trim()) c++;
    if (categoryId) c++;
    if (tagId) c++;
    if (difficulty) c++;
    return c;
  }, [debouncedSearch, categoryId, tagId, difficulty]);

  const hasActiveFilters = activeFilterCount > 0;

  const clearAll = useCallback(() => {
    setSearch("");
    setDebouncedSearch("");
    setCategoryId("");
    setTagId("");
    setDifficulty("");
  }, []);

  // --- Categories & Tags ---
  const { data: categoriesData, isLoading: catLoading } = useSWR<Category[]>(
    "/api/problems/categories",
    fetcher,
    { revalidateOnFocus: false }
  );
  const { data: tagsData, isLoading: tagLoading } = useSWR<Tag[]>(
    "/api/problems/tags",
    fetcher,
    { revalidateOnFocus: false }
  );
  const categories = categoriesData ?? [];
  const tags = tagsData ?? [];

  // --- Stats ---
  const { data: statsData } = useSWR<StatsData>("/api/problems/stats", fetcher, {
    revalidateOnFocus: false,
  });

  // --- Problems (Infinite Scroll) ---
  const queryKey = useMemo(() => {
    const p = new URLSearchParams();
    p.set("limit", String(LIMIT));
    if (debouncedSearch.trim()) p.set("search", debouncedSearch.trim());
    if (categoryId) p.set("category_id", categoryId);
    if (tagId) p.set("tag_id", tagId);
    if (difficulty) p.set("difficulty", difficulty);
    return p.toString();
  }, [debouncedSearch, categoryId, tagId, difficulty]);

  const getKey = (pageIndex: number, previousPageData: ProblemsResponse | null) => {
    if (previousPageData && previousPageData.data.length === 0) return null;
    const p = new URLSearchParams(queryKey);
    p.set("offset", String(pageIndex * LIMIT));
    return `/api/problems?${p.toString()}`;
  };

  const { data, error, isLoading, isValidating, size, setSize, mutate } =
    useSWRInfinite<ProblemsResponse>(getKey, fetcher, {
      revalidateOnFocus: false,
      dedupingInterval: 60_000,
    });

  const problems = useMemo(() => data?.flatMap((page) => page.data) ?? [], [data]);
  const totalCount = data?.[0]?.count ?? 0;
  const isEmpty = problems.length === 0;
  const hasMore = problems.length < totalCount;

  // IntersectionObserver
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

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [queryKey]);

  const filtersReady = !catLoading && !tagLoading;

  return (
    <main className="min-h-screen bg-white text-slate-900 antialiased">
      <div className="mx-auto max-w-7xl px-4 py-8 lg:px-6">
        {/* ==================== HERO (dark, own style) ==================== */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="relative mb-8 overflow-hidden rounded-2xl bg-[#121212] px-6 py-10 sm:px-10 sm:py-12"
        >
          <div className="relative">
            <div className="mb-6 flex items-center gap-3">
              <WindowChrome />
            </div>

            <h1 className="text-3xl font-bold leading-[1.15] tracking-tight text-white sm:text-4xl">
              Algoritmik Masalalar Maydoni
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/55">
              Bilimingizni sinab ko&apos;ring va reytingda o&apos;z o&apos;rningizni toping.
              Har bir masala — bu yangi algoritmik fikrlash imkoniyati.
            </p>
          </div>

          {/* Decorative gradient orb */}
          <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-[#D9AE55]/10 blur-3xl" />
        </motion.section>

        {/* ==================== STATS ==================== */}
        {!statsData ? (
          <StatsSkeleton />
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1, ease: "easeOut" }}
            className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3"
          >
            <StatCard
              icon={<Target className="size-5 text-[#D9AE55]" strokeWidth={1.5} />}
              label="Jami masalalar"
              value={statsData.total}
            />
            <StatCard
              icon={<CheckCircle2 className="size-5 text-emerald-600" strokeWidth={1.5} />}
              label="Yechilgan"
              value={statsData.solved}
            />
            <StatCard
              icon={<Hash className="size-5 text-slate-400" strokeWidth={1.5} />}
              label="Qolgan"
              value={Math.max(statsData.total - statsData.solved, 0)}
            />
          </motion.div>
        )}

        {/* ==================== GRID ==================== */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Desktop Sidebar */}
          <aside className="hidden lg:col-span-3 lg:block">
            <div className="sticky top-24 space-y-6">
              {!filtersReady ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <SidebarSkeleton />
                </div>
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <FilterPanel
                    search={search}
                    setSearch={setSearch}
                    categoryId={categoryId}
                    setCategoryId={setCategoryId}
                    tagId={tagId}
                    setTagId={setTagId}
                    difficulty={difficulty}
                    setDifficulty={setDifficulty}
                    categories={categories}
                    tags={tags}
                    hasActiveFilters={hasActiveFilters}
                    clearAll={clearAll}
                  />
                </div>
              )}
            </div>
          </aside>

          {/* Main Content */}
          <div className="lg:col-span-9">
            {/* Mobile Filter Toggle */}
            <div className="mb-4 lg:hidden">
              <button
                onClick={() => setMobileFiltersOpen((v) => !v)}
                className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300"
              >
                <span className="flex items-center gap-2">
                  <Terminal className="size-4 text-[#D9AE55]" strokeWidth={1.5} />
                  Filterlar
                  {activeFilterCount > 0 && (
                    <span className="rounded-full bg-[#D9AE55] px-2 py-0.5 text-[10px] font-bold text-[#121212]">
                      {activeFilterCount}
                    </span>
                  )}
                </span>
                <ChevronDown
                  className={`size-4 text-slate-400 transition-transform ${
                    mobileFiltersOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              {mobileFiltersOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  {!filtersReady ? (
                    <SidebarSkeleton />
                  ) : (
                    <MobileFilterContent
                      search={search}
                      setSearch={setSearch}
                      categoryId={categoryId}
                      setCategoryId={setCategoryId}
                      tagId={tagId}
                      setTagId={setTagId}
                      difficulty={difficulty}
                      setDifficulty={setDifficulty}
                      categories={categories}
                      tags={tags}
                      clearAll={clearAll}
                    />
                  )}
                </motion.div>
              )}
            </div>

            {/* Active Pills */}
            {hasActiveFilters && (
              <div className="mb-4 flex flex-wrap items-center gap-2">
                {debouncedSearch.trim() && (
                  <FilterPill label={`"${debouncedSearch}"`} onRemove={() => setSearch("")} />
                )}
                {difficulty && (
                  <FilterPill
                    label={
                      difficulty === "easy" ? "Oson" : difficulty === "medium" ? "O'rta" : "Qiyin"
                    }
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
                  className="text-xs font-medium text-slate-400 underline-offset-2 transition hover:text-[#D9AE55] hover:underline"
                >
                  Hammasini tozalash
                </button>
              </div>
            )}

            {/* Results count */}
            <div className="mb-3 flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-2 font-mono">
                <Hash className="size-3 text-slate-300" strokeWidth={1.5} />
                {isLoading && !data ? (
                  <span className="inline-flex items-center gap-1.5">
                    <Loader2 className="size-3 animate-spin" />
                    Yuklanmoqda...
                  </span>
                ) : (
                  <>
                    <span className="font-bold text-slate-700">{totalCount}</span> ta masala
                  </>
                )}
              </span>
              {isValidating && data && (
                <span className="inline-flex items-center gap-1.5 text-slate-300">
                  <Loader2 className="size-3 animate-spin" />
                  Yangilanmoqda
                </span>
              )}
            </div>

            {/* Table / Skeleton / Empty / Error */}
            {isLoading && !data ? (
              <TableSkeleton />
            ) : error ? (
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center shadow-sm">
                <AlertCircle className="mx-auto mb-3 size-8 text-slate-300" />
                <p className="text-sm font-medium text-slate-700">Yuklashda xatolik yuz berdi</p>
                <button
                  onClick={() => mutate()}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                >
                  <RotateCcw className="size-3.5" />
                  Qayta urinish
                </button>
              </div>
            ) : isEmpty && !isValidating ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center">
                <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-slate-50">
                  <Search className="size-5 text-slate-300" strokeWidth={1.5} />
                </div>
                <p className="mt-3 text-sm font-medium text-slate-900">Masalalar topilmadi</p>
                <p className="mt-1 text-xs text-slate-500">Boshqa filterlarni sinab ko&apos;ring</p>
                {hasActiveFilters && (
                  <button
                    onClick={clearAll}
                    className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-[#121212] px-4 py-2 text-xs font-medium text-white transition hover:bg-[#1a1a1a]"
                  >
                    <RotateCcw className="size-3.5" />
                    Filterlarni tozalash
                  </button>
                )}
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase tracking-wider text-slate-400">
                      <tr>
                        <th className="w-12 px-2 py-3 text-right" />
                        <th className="w-14 px-4 py-3 text-center">Holat</th>
                        <th className="min-w-[240px] px-4 py-3">Nomi</th>
                        <th className="px-4 py-3">Kategoriya</th>
                        <th className="px-4 py-3">Qiyinlik</th>
                        <th className="px-4 py-3 text-right">XP</th>
                        <th className="px-4 py-3 text-right">Qabul</th>
                        <th className="hidden px-4 py-3 xl:table-cell">Teglar</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {problems.map((problem, idx) => (
                        <ProblemRow key={`${problem.id}-${idx}`} problem={problem} index={idx} />
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Sentinel */}
                <div ref={sentinelRef} className="border-t border-slate-100 py-4 text-center">
                  {hasMore ? (
                    <Loader2 className="mx-auto size-5 animate-spin text-slate-400" />
                  ) : problems.length > 0 ? (
                    <span className="font-mono text-xs text-slate-400">// Barchasi yuklandi</span>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

/* ================================================================
   SUB-COMPONENTS
   ================================================================ */
function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
        <div className="flex size-8 items-center justify-center rounded-lg bg-slate-50 transition group-hover:bg-slate-100">
          {icon}
        </div>
      </div>
      <p className="mt-2 font-mono text-3xl font-bold tabular-nums tracking-tight text-slate-900">
        {value}
      </p>
    </div>
  );
}

function FilterPanel({
  search,
  setSearch,
  categoryId,
  setCategoryId,
  tagId,
  setTagId,
  difficulty,
  setDifficulty,
  categories,
  tags,
  hasActiveFilters,
  clearAll,
}: {
  search: string;
  setSearch: (v: string) => void;
  categoryId: string;
  setCategoryId: (v: string) => void;
  tagId: string;
  setTagId: (v: string) => void;
  difficulty: string;
  setDifficulty: (v: string) => void;
  categories: Category[];
  tags: Tag[];
  hasActiveFilters: boolean;
  clearAll: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <SlidersHorizontal className="size-4 text-[#D9AE55]" strokeWidth={1.5} />
          Filterlar
        </div>
        {hasActiveFilters && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
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
          className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-8 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-[#D9AE55]/60 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#D9AE55]/15"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-2.5 top-2.5 text-slate-400 transition hover:text-slate-600"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      {/* Difficulty */}
      <FilterSection title="Qiyinlik darajasi">
        <div className="space-y-1">
          {[
            { value: "easy", label: "Oson" },
            { value: "medium", label: "O'rta" },
            { value: "hard", label: "Qiyin" },
          ].map((d) => {
            const active = difficulty === d.value;
            return (
              <button
                key={d.value}
                onClick={() => setDifficulty(active ? "" : d.value)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                  active
                    ? "bg-[#121212] font-medium text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <span
                  className={`size-2 rounded-full ${
                    active ? "bg-[#D9AE55]" : "bg-slate-300"
                  }`}
                />
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
                    ? "bg-[#121212] font-medium text-white shadow-sm"
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
                    ? "border-[#121212] bg-[#121212] text-white shadow-sm"
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

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-slate-100 pt-5">
      <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h4>
      {children}
    </div>
  );
}

function FilterPill({ label, onRemove }: { label: string; onRemove: () => void }) {
  if (!label) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[#D9AE55]/30 bg-[#D9AE55]/10 px-2.5 py-1 text-xs font-medium text-[#B8943F]">
      {label}
      <button
        onClick={onRemove}
        className="ml-0.5 rounded-full p-0.5 transition hover:bg-[#D9AE55]/20"
      >
        <X className="size-3 text-[#D9AE55]/70" />
      </button>
    </span>
  );
}

function ProblemRow({ problem, index }: { problem: Problems; index: number }) {
  const lineNumber = (index + 1).toString().padStart(2, "0");

  return (
    <tr className="group transition-colors hover:bg-slate-50/60">
      <td className="px-2 py-3.5">
        <span className="block w-8 text-right font-mono text-xs text-slate-300">{lineNumber}</span>
      </td>
      <td className="px-4 py-3.5 text-center">
        {problem.solved ? (
          <div className="mx-auto flex size-6 items-center justify-center rounded-full bg-[#D9AE55]/10">
            <CheckCircle2 className="size-4 text-[#D9AE55]" strokeWidth={1.5} />
          </div>
        ) : (
          <span className="mx-auto block size-4 rounded-full border-2 border-slate-200 transition group-hover:border-slate-300" />
        )}
      </td>
      <td className="px-4 py-3.5">
        <Link
          href={`/problem/${problem.slug}`}
          className="font-medium text-slate-900 transition hover:text-[#B8943F] hover:underline"
        >
          {problem.title}
        </Link>
      </td>
      <td className="px-4 py-3.5 text-slate-500">{problem.category || "—"}</td>
      <td className="px-4 py-3.5">
        <DifficultyBadge difficulty={problem.difficulty} />
      </td>
      <td className="px-4 py-3.5 text-right font-mono font-medium tabular-nums text-slate-700">
        ⚡️ {problem.xp}
      </td>
      <td className="px-4 py-3.5 text-right font-mono tabular-nums text-slate-400">
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
            <span className="font-mono text-[11px] text-slate-400">+{problem.tags.length - 3}</span>
          )}
        </div>
      </td>
    </tr>
  );
}

function DifficultyBadge({ difficulty }: { difficulty: Problems["difficulty"] }) {
  const map: Record<string, { cls: string; lbl: string }> = {
    easy: {
      cls: "text-slate-600 border-slate-200 bg-slate-50",
      lbl: "Oson",
    },
    medium: {
      cls: "text-[#B8943F] border-[#D9AE55]/30 bg-[#D9AE55]/10",
      lbl: "O'rta",
    },
    hard: {
      cls: "text-slate-900 border-slate-300 bg-slate-100",
      lbl: "Qiyin",
    },
  };
  const d = map[difficulty] ?? {
    cls: "text-slate-600 border-slate-200 bg-slate-50",
    lbl: difficulty,
  };
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${d.cls}`}
    >
      {d.lbl}
    </span>
  );
}

function MobileFilterContent({
  search,
  setSearch,
  categoryId,
  setCategoryId,
  tagId,
  setTagId,
  difficulty,
  setDifficulty,
  categories,
  tags,
  clearAll,
}: {
  search: string;
  setSearch: (v: string) => void;
  categoryId: string;
  setCategoryId: (v: string) => void;
  tagId: string;
  setTagId: (v: string) => void;
  difficulty: string;
  setDifficulty: (v: string) => void;
  categories: Category[];
  tags: Tag[];
  clearAll: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-900">Filterlar</span>
        <button
          onClick={clearAll}
          className="text-xs font-medium text-slate-400 hover:text-[#D9AE55]"
        >
          Tozalash
        </button>
      </div>

      <input
        type="text"
        placeholder="Qidirish..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#D9AE55]/60 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#D9AE55]/15"
      />

      <div>
        <p className="mb-2 text-xs font-semibold text-slate-400">Qiyinlik</p>
        <div className="flex gap-2">
          {["easy", "medium", "hard"].map((d) => (
            <button
              key={d}
              onClick={() => setDifficulty(difficulty === d ? "" : d)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                difficulty === d
                  ? "bg-[#121212] text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {d === "easy" ? "Oson" : d === "medium" ? "O'rta" : "Qiyin"}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold text-slate-400">Kategoriya</p>
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:border-[#D9AE55]/60 focus:outline-none focus:ring-2 focus:ring-[#D9AE55]/15"
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
        <p className="mb-2 text-xs font-semibold text-slate-400">Teg</p>
        <select
          value={tagId}
          onChange={(e) => setTagId(e.target.value)}
          className="h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:border-[#D9AE55]/60 focus:outline-none focus:ring-2 focus:ring-[#D9AE55]/15"
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