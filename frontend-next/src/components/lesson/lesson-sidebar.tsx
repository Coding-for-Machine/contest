"use client";

import Link from "next/link";
import {
  Check,
  PlayCircle,
  Code2,
  HelpCircle,
  GraduationCap,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  LessonSelection,
  LessonSummary,
} from "@/lib/lesson/types";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

interface LessonSidebarProps {
  lesson: LessonSummary;
  selection: LessonSelection;
  onSelect: (sel: LessonSelection) => void;
  isLoading: boolean;
  courseSlug?: string;
}

function RowIcon({
  done,
  Icon,
}: {
  done: boolean;
  Icon: React.ComponentType<{ className?: string }>;
}) {
  if (done) {
    return (
      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-[#D9AE55] text-black">
        <Check className="size-3 stroke-[3]" />
      </span>
    );
  }

  return (
    <span className="flex size-5 shrink-0 items-center justify-center rounded-full border border-black/20 text-black/40">
      <Icon className="size-3" />
    </span>
  );
}

export function LessonSidebar({
  lesson,
  selection,
  onSelect,
  isLoading,
  courseSlug,
}: LessonSidebarProps) {
  const progress =
    lesson.tk > 0
      ? Math.round((lesson.us.ft / lesson.tk) * 100)
      : 0;

  const sortedLectures = [...lesson.lecs].sort(
    (a, b) => a.o - b.o
  );

  const backHref = courseSlug
    ? `/courses/${courseSlug}`
    : "/courses";

  return (
    <Sidebar
  collapsible="offcanvas"
  className="top-14 h-[calc(100vh-3.5rem)] border-r border-black/10 bg-white"
>
      {/* Header */}
      <SidebarHeader className="gap-3 border-b border-black/10 bg-white px-4 py-4">
        <Link
          href={backHref}
          className="flex items-center gap-2 text-xs text-black/40 transition hover:text-[#B88A2D]"
        >
          <ArrowLeft className="size-3" />
          Kursga qaytish
        </Link>

        <div className="flex items-center gap-2.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#D9AE55] text-black">
            <GraduationCap className="size-4" />
          </span>

          <h2 className="truncate text-sm font-semibold text-black/90">
            {lesson.t}
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/10">
            <div
              className="h-full rounded-full bg-[#D9AE55] transition-all"
              style={{
                width: `${progress}%`,
              }}
            />
          </div>

          <span className="shrink-0 text-xs tabular-nums text-black/40">
            {lesson.us.ft}/{lesson.tk}
          </span>
        </div>
      </SidebarHeader>

      {/* Content */}
      <SidebarContent className="bg-white px-1.5 py-2">
        {/* Ma'ruzalar */}
        {sortedLectures.length > 0 && (
          <SidebarGroup>
            <SidebarGroupLabel className="px-2 text-[11px] font-semibold uppercase tracking-wide text-black/30">
              Ma&apos;ruzalar
            </SidebarGroupLabel>

            <SidebarGroupContent>
              <SidebarMenu>
                {sortedLectures.map((lec) => {
                  const active =
                    selection.type === "lecture" &&
                    selection.slug === lec.s;

                  return (
                    <SidebarMenuItem key={lec.id}>
                      <SidebarMenuButton
                        isActive={active}
                        disabled={isLoading && active}
                        onClick={() =>
                          onSelect({
                            type: "lecture",
                            slug: lec.s,
                          })
                        }
                        className={cn(
                          "gap-2 rounded-md text-sm text-black/70 transition",

                          active &&
                            "bg-[#D9AE55]/10 font-medium text-[#B88A2D] hover:bg-[#D9AE55]/10",

                          !active &&
                            "hover:bg-black/5 hover:text-black"
                        )}
                      >
                        <RowIcon
                          done={lec.done}
                          Icon={PlayCircle}
                        />

                        <span className="truncate">
                          {lec.t}
                        </span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Masalalar */}
        {lesson.probs.length > 0 && (
          <SidebarGroup>
            <SidebarGroupLabel className="px-2 text-[11px] font-semibold uppercase tracking-wide text-black/30">
              Masalalar
            </SidebarGroupLabel>

            <SidebarGroupContent>
              <SidebarMenu>
                {lesson.probs.map((p) => {
                  const active =
                    selection.type === "problem" &&
                    selection.slug === p.s;

                  return (
                    <SidebarMenuItem key={p.id}>
                      <SidebarMenuButton
                        isActive={active}
                        disabled={isLoading && active}
                        onClick={() =>
                          onSelect({
                            type: "problem",
                            slug: p.s,
                          })
                        }
                        className={cn(
                          "gap-2 rounded-md text-sm text-black/70 transition",

                          active &&
                            "bg-[#D9AE55]/10 font-medium text-[#B88A2D] hover:bg-[#D9AE55]/10",

                          !active &&
                            "hover:bg-black/5 hover:text-black"
                        )}
                      >
                        <RowIcon
                          done={p.done}
                          Icon={Code2}
                        />

                        <span className="min-w-0 flex-1 truncate">
                          {p.t}
                        </span>

                        <span className="shrink-0 text-xs text-black/30">
                          {p.xp} XP
                        </span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Savollar */}
        {lesson.qs.length > 0 && (
          <SidebarGroup>
            <SidebarGroupLabel className="px-2 text-[11px] font-semibold uppercase tracking-wide text-black/30">
              Savollar
            </SidebarGroupLabel>

            <SidebarGroupContent>
              <SidebarMenu>
                {lesson.qs.map((q, i) => {
                  const active =
                    selection.type === "quiz" &&
                    selection.id === q.id;

                  return (
                    <SidebarMenuItem key={q.id}>
                      <SidebarMenuButton
                        isActive={active}
                        disabled={isLoading && active}
                        onClick={() =>
                          onSelect({
                            type: "quiz",
                            id: q.id,
                          })
                        }
                        className={cn(
                          "gap-2 rounded-md text-sm text-black/70 transition",

                          active &&
                            "bg-[#D9AE55]/10 font-medium text-[#B88A2D] hover:bg-[#D9AE55]/10",

                          !active &&
                            "hover:bg-black/5 hover:text-black"
                        )}
                      >
                        <RowIcon
                          done={q.done}
                          Icon={HelpCircle}
                        />

                        <span className="flex-1 truncate">
                          Savol {i + 1}
                        </span>

                        <span className="shrink-0 text-xs text-black/30">
                          {q.xp} XP
                        </span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>
    </Sidebar>
  );
}