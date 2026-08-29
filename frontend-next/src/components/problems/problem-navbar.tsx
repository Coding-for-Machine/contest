"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ChevronLeft,
  ChevronRight,
  List,
  Shuffle,
  Play,
  Loader2,
  NotebookPen,
  Sparkles,
  LayoutPanelLeft,
  Settings,
  Flame,
  Timer,
  Users,
  Crown,
  CloudUpload,
  ListRestart,
  ListIndentDecrease,
  ReplyAll,
  CircleArrowLeft,
  SquareArrowLeft,
  
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { ProblemsListSheet } from "./problems-list-sheet";

interface ProblemNavbarProps {
  slug: string;
  onRun?: () => void;
  onSubmit?: () => void;
  isRunning?: boolean;
  isSubmitting?: boolean;
  streakCount?: number;

  /** Navigatsiya: oldingi/keyingi/tasodifiy masalaga o'tish */
  onPrev?: () => void;
  onNext?: () => void;
  onRandom?: () => void;
  isNavigating?: boolean;
  hasPrev?: boolean;
  hasNext?: boolean;

  /**
   * Hozircha backendga ulanmagan tugmalar (Qaydlar, AI, Joylashuv, Sozlamalar,
   * Vaqt, Hamkorlik) bosilganda chaqiriladi — ProblemWorkspace buni konsolga
   * xabar chiqarish uchun ishlatadi.
   */
  onAction?: (label: string) => void;
}

function IconButton({
  label,
  active,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      className={cn(
        "relative flex h-8 w-8 items-center justify-center rounded-md text-neutral-500 transition-colors",
        "hover:bg-neutral-100 hover:text-neutral-900",
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent",
        active && "bg-neutral-100 text-neutral-900",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function ProblemNavbar({
  slug,
  onRun,
  onSubmit,
  isRunning,
  isSubmitting,
  streakCount = 0,
  onPrev,
  onNext,
  onRandom,
  isNavigating,
  hasPrev = true,
  hasNext = true,
  onAction,
}: ProblemNavbarProps) {
  const { user, isAuthenticated } = useAuth();
  const [notesOpen, setNotesOpen] = useState(false);
  const [problemsListOpen, setProblemsListOpen] = useState(false);

  const handleNotes = () => {
    setNotesOpen((v) => !v);
    onAction?.("Qaydlar paneli hali ishlab chiqilmoqda (UI namoyishi)");
  };

  return (
    <header className="flex h-14 w-full shrink-0 items-center justify-between border-b border-neutral-200 bg-white px-3">
      {/* Chap qism: navigatsiya */}
      <div className="flex items-center gap-1">
        <Link
          href="/problems"
          className="flex h-8 w-8 items-center justify-center rounded-md text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          aria-label="Bosh sahifa"
        >
          {/* <ListRestart /> */}
          {/* <ReplyAll size={18} /> */}
          {/* <CircleArrowLeft size={18}/> */}
          <SquareArrowLeft size={18}/>
        </Link>

        <div className="mx-1 h-5 w-px bg-neutral-200" />

        <button
          type="button"
          title="Masalalar ro'yxati"
          onClick={() => setProblemsListOpen(true)}
          className="flex h-8 w-8 items-center justify-center rounded-md text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        >
          <List className="size-[18px]" />
        </button>

        <div className="flex items-center">
          <IconButton
            label="Oldingi masala"
            onClick={onPrev}
            disabled={isNavigating || !hasPrev}
          >
            <ChevronLeft className="size-[18px]" />
          </IconButton>
          <IconButton
            label="Keyingi masala"
            onClick={onNext}
            disabled={isNavigating || !hasNext}
          >
            <ChevronRight className="size-[18px]" />
          </IconButton>
        </div>

        <IconButton
          label="Tasodifiy masala"
          onClick={onRandom}
          disabled={isNavigating}
        >
          {isNavigating ? (
            <Loader2 className="size-[18px] animate-spin" />
          ) : (
            <Shuffle className="size-[18px]" />
          )}
        </IconButton>
      </div>

      {/* Markaz: Run / Submit */}
      <div className="flex items-center gap-2 ml-74">
        <button
          type="button"
          onClick={onRun}
          disabled={isRunning || isSubmitting}
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-neutral-50 px-3 text-sm font-medium text-neutral-700 transition-colors",
            "hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {isRunning ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Play className="size-4" />
          )}
          Yuritish
        </button>

        <button
          type="button"
          onClick={onSubmit}
          disabled={isRunning || isSubmitting}
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-md bg-green-600 px-3 text-sm font-medium text-white transition-colors",
            "hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {isSubmitting ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <CloudUpload  className="size-4"/>
          )}
          Yuborish
        </button>
      </div>

      {/* O'ng qism: vositalar va profil */}
      <div className="flex items-center gap-0.5">
        <IconButton label="Qaydlar" active={notesOpen} onClick={handleNotes}>
          <NotebookPen className="size-[18px]" />
        </IconButton>

        <IconButton
          label="AI yordamchi"
          onClick={() =>
            onAction?.("AI yordamchi hali ishlab chiqilmoqda (UI namoyishi)")
          }
        >
          <Sparkles className="size-[18px]" />
        </IconButton>

        <IconButton
          label="Joylashuv sozlamalari"
          onClick={() =>
            onAction?.("Joylashuv sozlamalari hali ishlab chiqilmoqda (UI namoyishi)")
          }
        >
          <LayoutPanelLeft className="size-[18px]" />
        </IconButton>

        <IconButton
          label="Sozlamalar"
          onClick={() =>
            onAction?.("Umumiy sozlamalar hali ishlab chiqilmoqda (UI namoyishi)")
          }
        >
          <Settings className="size-[18px]" />
        </IconButton>

        <div className="mx-1 h-5 w-px bg-neutral-200" />

        <div
          className="flex h-8 items-center gap-1 rounded-md px-2 text-sm text-neutral-500"
          title="Kunlik seriya"
        >
          <Flame className="size-4 text-orange-400" />
          <span className="tabular-nums">{streakCount}</span>
        </div>

        <IconButton
          label="Vaqt hisoblagich"
          onClick={() =>
            onAction?.("Vaqt hisoblagich hali ishlab chiqilmoqda (UI namoyishi)")
          }
        >
          <Timer className="size-[18px]" />
        </IconButton>

        <IconButton
          label="Boshqalar bilan ulanish"
          onClick={() =>
            onAction?.("Hamkorlikda yechish hali ishlab chiqilmoqda (UI namoyishi)")
          }
        >
          <Users className="size-[18px]" />
        </IconButton>

        <div className="mx-1 h-5 w-px bg-neutral-200" />

        {/* Foydalanuvchi — useAuth() (localStorage asosida) dan olinadi */}
        {isAuthenticated && user ? (
          <div
            className="flex h-8 items-center gap-1.5 rounded-md px-1.5 text-sm text-neutral-600"
            title={user.username}
          >
            <span className="flex size-6 items-center justify-center rounded-full bg-orange-100 text-[11px] font-semibold text-orange-600">
              {user.username?.slice(0, 1).toUpperCase() ?? "?"}
            </span>
            <span className="hidden max-w-[100px] truncate font-medium sm:inline">
              {user.username}
            </span>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex h-8 items-center rounded-md px-2 text-sm font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            Kirish
          </Link>
        )}

        <button
          type="button"
          className="ml-1 flex h-8 items-center gap-1.5 rounded-md bg-amber-100 px-3 text-sm font-medium text-amber-700 transition-colors hover:bg-amber-200"
        >
          <Crown className="size-[15px]" />
          Premium
        </button>
      </div>

      <ProblemsListSheet
        open={problemsListOpen}
        onClose={() => setProblemsListOpen(false)}
        currentSlug={slug}
      />
    </header>
  );
}