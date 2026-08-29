"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { X, Search, CheckCircle2, Loader2, AlertTriangle, RotateCcw } from "lucide-react";
import { getProblemsList } from "@/lib/problems/api";
import type { Problems } from "@/lib/problems/types";
import { DIFFICULTY_LABELS, DIFFICULTY_CLASSES } from "@/lib/problems/utils";
import { cn } from "@/lib/utils";

interface ProblemsListSheetProps {
  open: boolean;
  onClose: () => void;
  currentSlug: string;
}

const PAGE_SIZE = 20;

function useDebounce<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function ProblemsListSheet({
  open,
  onClose,
  currentSlug,
}: ProblemsListSheetProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [allProblems, setAllProblems] = useState<Problems[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const debouncedQuery = useDebounce(query, 300);

  // Query o'zgarganda offset va listni reset qilish
  useEffect(() => {
    setOffset(0);
    setAllProblems([]);
    setHasMore(true);
  }, [debouncedQuery]);

  const { data, isLoading, error, mutate } = useSWR(
    open ? `problems-list-${debouncedQuery}-${offset}` : null,
    () =>
      getProblemsList({
        limit: PAGE_SIZE,
        offset,
        search: debouncedQuery,
      }),
    {
      keepPreviousData: true,
      revalidateOnFocus: false,
      onSuccess: (fresh) => {
        setAllProblems((prev) =>
          offset === 0 ? fresh.data : [...prev, ...fresh.data]
        );
        setHasMore(fresh.data.length === PAGE_SIZE);
      },
    }
  );

  // Escape yopish
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  // Infinite scroll: oxiriga yetganda yana yuklash
  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el || isLoading || !hasMore) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    if (nearBottom && !isLoading) {
      setOffset((prev) => prev + PAGE_SIZE);
    }
  }, [isLoading, hasMore]);

  const handleProblemClick = (slug: string) => {
    onClose();
    if (slug !== currentSlug) {
      router.push(`/problem/${slug}`);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      <button
        type="button"
        aria-label="Yopish"
        onClick={onClose}
        className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"
      />

      <div className="relative flex h-full w-full flex-col bg-white shadow-2xl animate-in slide-in-from-left duration-200 sm:w-1/2 sm:max-w-xl">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-5 py-4">
          <h2 className="text-lg font-semibold text-neutral-900">
            Masalalar ro'yxati
          </h2>
          <button
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            aria-label="Yopish"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Search */}
        <div className="shrink-0 border-b border-neutral-200 px-5 py-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-neutral-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Masala nomini qidiring..."
              className="w-full rounded-lg border border-neutral-200 bg-neutral-50 py-2 pl-9 pr-3 text-sm text-neutral-700 transition-colors focus:border-orange-500 focus:bg-white focus:outline-none"
              autoFocus
            />
          </div>
        </div>

        {/* List */}
        <div
          ref={scrollRef}
          onScroll={onScroll}
          className="flex-1 overflow-y-auto"
        >
          {error && offset === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
              <AlertTriangle className="size-8 text-neutral-300" />
              <div>
                <p className="text-sm font-medium text-neutral-600">
                  Ro'yxatni yuklashda xatolik
                </p>
                <p className="mt-0.5 text-xs text-neutral-400">
                  Internet aloqasini tekshirib ko'ring
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
          ) : allProblems.length === 0 && !isLoading ? (
            <div className="flex h-full items-center justify-center text-sm text-neutral-400">
              {debouncedQuery ? "Hech narsa topilmadi" : "Masalar mavjud emas"}
            </div>
          ) : (
            <ul className="divide-y divide-neutral-100">
              {allProblems.map((p) => {
                const isActive = p.slug === currentSlug;
                return (
                  <li key={`${p.id}-${p.slug}`}>
                    <button
                      type="button"
                      onClick={() => handleProblemClick(p.slug)}
                      className={cn(
                        "flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-neutral-50",
                        isActive && "bg-orange-50 hover:bg-orange-50"
                      )}
                    >
                      <span className="flex size-5 shrink-0 items-center justify-center">
                        {p.solved ? (
                          <CheckCircle2 className="size-4 text-emerald-500" />
                        ) : (
                          <span className="size-1.5 rounded-full bg-neutral-300" />
                        )}
                      </span>

                      <span className="min-w-0 flex-1">
                        <span
                          className={cn(
                            "block truncate text-sm font-medium",
                            isActive ? "text-orange-700" : "text-neutral-800"
                          )}
                        >
                          {p.title}
                        </span>
                        {p.category && (
                          <span className="block truncate text-xs text-neutral-400">
                            {p.category}
                          </span>
                        )}
                      </span>

                      <span
                        className={cn(
                          "shrink-0 rounded px-2 py-0.5 text-[11px] font-medium",
                          DIFFICULTY_CLASSES[p.difficulty]
                        )}
                      >
                        {DIFFICULTY_LABELS[p.difficulty]}
                      </span>
                    </button>
                  </li>
                );
              })}

              {/* Loading more */}
              {isLoading && (
                <li className="flex items-center justify-center py-4">
                  <Loader2 className="size-5 animate-spin text-neutral-400" />
                </li>
              )}

              {/* End of list */}
              {!hasMore && allProblems.length > 0 && (
                <li className="py-3 text-center text-xs text-neutral-400">
                  Barcha masalalar yuklandi
                </li>
              )}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}