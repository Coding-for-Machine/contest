"use client";

import { useState } from "react";
import useSWR from "swr";
import type { ProblemDetail } from "@/lib/problems/types";
import { getSolutionVideo } from "@/lib/problems/api";
import { SubmissionList } from "./submission-list";
import { MarkdownRenderer } from "../MarkdownRenderer";
import { VideoPlayer } from "../VideoPlayer"; // ← sizning pleer
import {
  Zap,
  Timer,
  MemoryStick,
  BadgeCheck,
  Lightbulb,
  ListChecks,
  PlayCircle,
  Lock,
} from "lucide-react";
import { DIFFICULTY_LABELS, DIFFICULTY_CLASSES } from "@/lib/problems/utils";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Tab = "description" | "hints" | "challenges" | "submissions" | "video";

interface DescriptionPanelProps {
  problem: ProblemDetail;
}

export function DescriptionPanel({ problem }: DescriptionPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("description");

  const hasHints = problem.hints.length > 0;
  const hasChallenges = problem.chall.length > 0;
  const hasVideo = problem.solved; // Faqat yechilgan masalada video tabi ko'rinadi

  // Video ma'lumotlarini faqat "video" tab ochilganda yuklaymiz
  const {
    data: videoData,
    isLoading: videoLoading,
    error: videoError,
  } = useSWR(
    hasVideo && activeTab === "video" ? `video-${problem.slug}` : null,
    () => getSolutionVideo(problem.slug),
    { revalidateOnFocus: false }
  );

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="flex shrink-0 items-center gap-0.5 overflow-x-auto border-b border-neutral-200 bg-white px-1">
        <TabButton
          active={activeTab === "description"}
          onClick={() => setActiveTab("description")}
          label="Tavsif"
        />
        {hasHints && (
          <TabButton
            active={activeTab === "hints"}
            onClick={() => setActiveTab("hints")}
            label="Maslahatlar"
            count={problem.hints.length}
          />
        )}
        {hasChallenges && (
          <TabButton
            active={activeTab === "challenges"}
            onClick={() => setActiveTab("challenges")}
            label="Talablar"
            count={problem.chall.length}
          />
        )}
        {hasVideo && (
          <TabButton
            active={activeTab === "video"}
            onClick={() => setActiveTab("video")}
            label="Video yechim"
            icon={<PlayCircle className="size-3.5" />}
          />
        )}
        <TabButton
          active={activeTab === "submissions"}
          onClick={() => setActiveTab("submissions")}
          label="Taqdimotlar"
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "description" && <DescriptionContent problem={problem} />}
        {activeTab === "hints" && <HintsContent problem={problem} />}
        {activeTab === "challenges" && <ChallengesContent problem={problem} />}
        {activeTab === "video" && (
          <VideoTab
            videoData={videoData}
            loading={videoLoading}
            error={videoError}
          />
        )}
        {activeTab === "submissions" && (
          <div className="p-6">
            <SubmissionList slug={problem.slug} />
          </div>
        )}
      </div>
    </div>
  );
}

// ========== VIDEO TAB ==========
function VideoTab({
  videoData,
  loading,
  error,
}: {
  videoData?: { hls_url: string; thumbnail: string | null; duration: number | null };
  loading: boolean;
  error: any;
}) {
  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-neutral-400">
        <div className="size-6 animate-spin rounded-full border-2 border-neutral-300 border-t-orange-500" />
        <span className="ml-2 text-sm">Video yuklanmoqda...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-neutral-400">
        <Lock className="size-8" />
        <p className="text-sm font-medium">Videoni ko'rish mumkin emas</p>
        <p className="text-xs text-neutral-400">
          {error.message || "Avval masalani yeching"}
        </p>
      </div>
    );
  }

  if (!videoData?.hls_url) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-neutral-400">
        <p className="text-sm">Ushbu masala uchun video mavjud emas</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <VideoPlayer
        src={videoData.hls_url}
        poster={videoData.thumbnail}
        title="Masala yechimi"
      />
      <p className="mt-3 text-xs text-neutral-400">
        Videoni tomosha qilish uchun klaviatura boshqaruvidan foydalanishingiz mumkin: Space (play/pause), ← → (oldinga/orqaga), F (fullscreen)
      </p>
    </div>
  );
}

// ========== UPDATED TabButton ==========
function TabButton({
  active,
  onClick,
  label,
  count,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative flex shrink-0 items-center gap-1.5 px-4 py-3 text-sm font-medium transition-colors",
        active ? "text-orange-600" : "text-neutral-500 hover:text-neutral-700"
      )}
    >
      {icon}
      {label}
      {typeof count === "number" && (
        <span
          className={cn(
            "flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-semibold tabular-nums",
            active
              ? "bg-orange-100 text-orange-600"
              : "bg-neutral-100 text-neutral-500"
          )}
        >
          {count}
        </span>
      )}
      {active && (
        <span className="absolute bottom-0 left-0 h-0.5 w-full bg-orange-500" />
      )}
    </button>
  );
}


function DescriptionContent({ problem }: { problem: ProblemDetail }) {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="mb-3 text-2xl font-bold text-neutral-900">
            {problem.title}
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              className={`border px-2.5 py-0.5 text-xs ${DIFFICULTY_CLASSES[problem.dif]}`}
            >
              {DIFFICULTY_LABELS[problem.dif]}
            </Badge>
            {problem.cate_name && (
              <Badge variant="outline" className="px-2.5 py-0.5 text-xs">
                {problem.cate_name}
              </Badge>
            )}
            {problem.tags.map((tag) => (
              <Badge
                key={tag.id}
                variant="outline"
                className="px-2.5 py-0.5 text-xs font-normal"
              >
                #{tag.name}
              </Badge>
            ))}
          </div>
        </div>

        {problem.solved && (
          <div className="flex shrink-0 items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-600">
            <BadgeCheck className="size-4" />
            Yechim topildi
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        <MetaItem
          icon={<Zap className="size-4 text-orange-500" />}
          label="XP"
          value={String(problem.xp)}
        />
        <MetaItem
          icon={<Timer className="size-4 text-orange-500" />}
          label="Vaqt limiti"
          value={`${problem.time_l} s`}
        />
        <MetaItem
          icon={<MemoryStick className="size-4 text-orange-500" />}
          label="Xotira limiti"
          value={`${problem.memory_l} MB`}
        />
      </div>

      {/* Description */}
      <MarkdownRenderer content={problem.desc} />
    </div>
  );
}

function HintsContent({ problem }: { problem: ProblemDetail }) {
  if (problem.hints.length === 0) {
    return (
      <EmptyTabState
        icon={<Lightbulb className="size-8" />}
        text="Maslahatlar mavjud emas"
      />
    );
  }

  return (
    <div className="space-y-3 p-6">
      {problem.hints.map((h, i) => (
        <div
          key={h.id}
          className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
        >
          <div className="mb-1.5 flex items-center gap-1.5 font-semibold">
            <Lightbulb className="size-4" />
            Maslahat {i + 1}
          </div>
          <MarkdownRenderer content={h.text} />
        </div>
      ))}
    </div>
  );
}

function ChallengesContent({ problem }: { problem: ProblemDetail }) {
  if (problem.chall.length === 0) {
    return (
      <EmptyTabState
        icon={<ListChecks className="size-8" />}
        text="Qo'shimcha talablar mavjud emas"
      />
    );
  }

  return (
    <div className="p-6">
      <ul className="space-y-3">
        {problem.chall.map((c, i) => (
          <li
            key={c.id}
            className="flex gap-3 rounded-xl border border-neutral-200 bg-white p-4"
          >
            <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-orange-100 text-[11px] font-semibold text-orange-600">
              {i + 1}
            </span>
            <div className="text-sm text-neutral-700">
              <MarkdownRenderer content={c.text} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function EmptyTabState({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 py-16 text-neutral-300">
      {icon}
      <p className="text-sm text-neutral-400">{text}</p>
    </div>
  );
}

function MetaItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-3">
      <div className="mb-1 flex items-center gap-1.5 text-xs text-neutral-400">
        {icon}
        {label}
      </div>
      <p className="text-sm font-semibold text-neutral-900">{value}</p>
    </div>
  );
}