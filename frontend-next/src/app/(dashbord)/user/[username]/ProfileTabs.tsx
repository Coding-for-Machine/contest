"use client";

import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  XCircle,
  Trophy,
  GraduationCap,
  Award,
  ExternalLink,
  Download,
} from "lucide-react";
import { SOURCE_TYPE_LABELS, type CertificateSourceType } from "@/lib/levels";
import type { ActivityResponse, CertificatesResponse, UserCoursesResponse, HistoryResponse } from "@/lib/types/users";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("uz-UZ", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 py-16 text-center text-sm text-white/40">
      {text}
    </div>
  );
}

/* ---- SKELETONS (content-shape, spinner emas — CLS bo'lmasin) ---- */

function ListRowSkeleton() {
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <div className="size-4 shrink-0 rounded-full bg-white/10 animate-pulse" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="h-3 w-2/3 rounded bg-white/10 animate-pulse" />
        <div className="h-2 w-1/3 rounded bg-white/5 animate-pulse" />
      </div>
      <div className="h-5 w-16 shrink-0 rounded-full bg-white/10 animate-pulse" />
    </li>
  );
}

function ListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <ul className="divide-y divide-white/5 rounded-2xl border border-white/10 bg-[#121212]">
      {Array.from({ length: rows }).map((_, i) => (
        <ListRowSkeleton key={i} />
      ))}
    </ul>
  );
}

function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#121212] p-5">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="h-4 w-3/5 rounded bg-white/10 animate-pulse" />
        <div className="h-5 w-16 shrink-0 rounded-full bg-white/5 animate-pulse" />
      </div>
      <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div className="h-full w-1/3 rounded-full bg-white/15 animate-pulse" />
      </div>
      <div className="h-3 w-2/5 rounded bg-white/5 animate-pulse" />
    </div>
  );
}

function GridSkeleton({ cards = 4 }: { cards?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {Array.from({ length: cards }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

function CertCardSkeleton() {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-[#121212] p-5">
      <div className="size-10 shrink-0 rounded-full bg-white/10 animate-pulse" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="h-2.5 w-1/4 rounded bg-white/5 animate-pulse" />
        <div className="h-3.5 w-3/4 rounded bg-white/10 animate-pulse" />
        <div className="h-2.5 w-2/5 rounded bg-white/5 animate-pulse" />
        <div className="flex gap-3 pt-1">
          <div className="h-3 w-16 rounded bg-white/5 animate-pulse" />
          <div className="h-3 w-10 rounded bg-white/5 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

function CertGridSkeleton({ cards = 4 }: { cards?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {Array.from({ length: cards }).map((_, i) => (
        <CertCardSkeleton key={i} />
      ))}
    </div>
  );
}

/* ---- ACTIVITY ---- */
function ActivityTab({ username }: { username: string }) {
  const { data, isLoading } = useSWR<ActivityResponse>(
    `/api/user/${username}/activity?limit=20`,
    fetcher,
    { dedupingInterval: 60_000 }
  );

  if (isLoading) return <ListSkeleton rows={6} />;
  if (!data || data.activity.length === 0)
    return <EmptyState text="Hali hech qanday faollik qayd etilmagan." />;

  return (
    <ul className="divide-y divide-white/5 rounded-2xl border border-white/10 bg-[#121212]">
      {data.activity.map((item) => (
        <li key={`${item.type}-${item.id}`} className="flex items-center gap-3 px-4 py-3">
          {item.type === "submission" && (
            <CheckCircle2 className="size-4 shrink-0 text-[#D9AE55]" />
          )}
          {item.type === "test" && (
            <GraduationCap className="size-4 shrink-0 text-[#D9AE55]" />
          )}
          {item.type === "contest" && (
            <Trophy className="size-4 shrink-0 text-[#D9AE55]" />
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{item.title}</p>
            <p className="text-xs text-white/40">{formatDate(item.timestamp)}</p>
          </div>
          {item.type === "submission" && (
            <Badge
              variant={item.verdict === "AC" ? "default" : "outline"}
              className={item.verdict === "AC" ? "bg-[#D9AE55] text-[#121212]" : "border-white/20 text-white/60"}
            >
              {item.verdict_display}
            </Badge>
          )}
          {item.type === "test" && (
            <span className="text-sm font-semibold text-[#D9AE55]">+{item.xp} XP</span>
          )}
          {item.type === "contest" && (
            <span className="text-sm font-semibold text-white">
              {item.rank ? `#${item.rank} o'rin` : `+${item.xp} XP`}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

/* ---- COURSES ---- */
function CoursesTab({ username }: { username: string }) {
  const { data, isLoading } = useSWR<UserCoursesResponse>(
    `/api/user/${username}/courses`,
    fetcher,
    { dedupingInterval: 90_000 }
  );

  if (isLoading) return <GridSkeleton cards={4} />;
  if (!data || data.courses.length === 0)
    return <EmptyState text="Hali birorta kursga yozilmagan." />;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {data.courses.map((enr) => (
        <Link
          key={enr.course.id}
          href={`/courses/${enr.course.slug}`}
          className="group rounded-2xl border border-white/10 bg-[#121212] p-5 transition hover:border-[#D9AE55]/40"
        >
          <div className="mb-3 flex items-start justify-between gap-2">
            <h4 className="font-semibold text-white group-hover:text-[#D9AE55] transition-colors">
              {enr.course.title}
            </h4>
            {enr.is_completed && (
              <Badge className="shrink-0 bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                Tugallangan
              </Badge>
            )}
          </div>

          <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-[#D9AE55] transition-all"
              style={{ width: `${enr.progress_percent}%` }}
            />
          </div>
          <p className="text-xs text-white/40">
            {enr.finished_lessons}/{enr.total_lessons} dars · {enr.finished_tests}/
            {enr.total_tests} test · {enr.progress_percent}%
          </p>
        </Link>
      ))}
    </div>
  );
}

/* ---- CERTIFICATES ---- */
function CertificatesTab({ username }: { username: string }) {
  const { data, isLoading } = useSWR<CertificatesResponse>(
    `/api/user/${username}/certificates`,
    fetcher,
    { dedupingInterval: 5 * 60_000, revalidateOnFocus: false }
  );

  if (isLoading) return <CertGridSkeleton cards={4} />;
  if (!data || data.certificates.length === 0)
    return <EmptyState text="Hali birorta sertifikat qo'lga kiritilmagan." />;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {data.certificates.map((cert) => (
        <div
          key={cert.id}
          className="flex items-start gap-3 rounded-2xl border border-white/10 bg-[#121212] p-5"
        >
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#D9AE55]/10">
            <Award className="size-5 text-[#D9AE55]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="mb-0.5 text-xs font-medium uppercase tracking-wide text-[#D9AE55]">
              {SOURCE_TYPE_LABELS[cert.source_type as CertificateSourceType]}
            </p>
            <h4 className="truncate font-semibold text-white">{cert.source_title}</h4>
            <p className="mb-3 text-xs text-white/40">
              {cert.certificate_code} · {formatDate(cert.issued_at)}
            </p>
            <div className="flex items-center gap-3 text-xs font-medium">
              <a
                href={cert.verify_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-white/60 hover:text-[#D9AE55] transition-colors"
              >
                <ExternalLink className="size-3.5" /> Tekshirish
              </a>
              {cert.pdf_url && (
                <a
                  href={cert.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-white/60 hover:text-[#D9AE55] transition-colors"
                >
                  <Download className="size-3.5" /> PDF
                </a>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- HISTORY ---- */
function HistoryTab({ telegramId }: { telegramId: number }) {
  const { data, isLoading } = useSWR<HistoryResponse>(
    `/api/user/history/${telegramId}?limit=15`,
    fetcher,
    { revalidateOnFocus: false }
  );

  if (isLoading) return <ListSkeleton rows={6} />;
  if (!data || data.results.length === 0)
    return <EmptyState text="Hali birorta masala yechilmagan." />;

  return (
    <ul className="divide-y divide-white/5 rounded-2xl border border-white/10 bg-[#121212]">
      {data.results.map((sub) => (
        <li key={sub.id} className="flex items-center gap-3 px-4 py-3">
          {sub.verdict === "AC" ? (
            <CheckCircle2 className="size-4 shrink-0 text-[#D9AE55]" />
          ) : (
            <XCircle className="size-4 shrink-0 text-white/20" />
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">
              {sub.problem.title}
            </p>
            <p className="text-xs text-white/40">
              {sub.language ?? "—"} · {formatDate(sub.submitted_at)}
            </p>
          </div>
          <span className="text-xs text-white/30">{sub.progress}</span>
          <Badge
            variant={sub.verdict === "AC" ? "default" : "outline"}
            className={sub.verdict === "AC" ? "bg-[#D9AE55] text-[#121212]" : "border-white/20 text-white/60"}
          >
            {sub.verdict_display}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

/* ---- MAIN ---- */
export function ProfileTabs({
  username,
  telegramId,
}: {
  username: string;
  telegramId: number;
}) {
  return (
    <Tabs defaultValue="activity" className="w-full">
      <TabsList className="mb-6 h-auto w-full justify-start gap-1 bg-transparent p-0 sm:w-fit">
        {[
          { value: "activity", label: "Faoliyat" },
          { value: "courses", label: "Kurslar" },
          { value: "certificates", label: "Sertifikatlar" },
          { value: "history", label: "Yechimlar" },
        ].map((tab) => (
          <TabsTrigger
            key={tab.value}
            value={tab.value}
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/60 transition data-[state=active]:border-[#D9AE55] data-[state=active]:bg-[#D9AE55] data-[state=active]:text-[#121212]"
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>

      <TabsContent value="activity">
        <ActivityTab username={username} />
      </TabsContent>
      <TabsContent value="courses">
        <CoursesTab username={username} />
      </TabsContent>
      <TabsContent value="certificates">
        <CertificatesTab username={username} />
      </TabsContent>
      <TabsContent value="history">
        <HistoryTab telegramId={telegramId} />
      </TabsContent>
    </Tabs>
  );
}