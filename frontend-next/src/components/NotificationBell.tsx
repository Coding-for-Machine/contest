"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  Bell,
  CheckCircle2,
  XCircle,
  Trash2,
  Loader2,
  CheckCheck,
  Trophy,
  BookOpen,
  Info,
  Zap,
  Clock,
  X,
} from "lucide-react";
import { useSSEEvent } from "@/hooks/useSSEEvent";
import { useAuth } from "@/context/AuthContext";
import type { NotificationPayload } from "@/lib/sse/types";
import type { NotificationItem } from "@/lib/problems/api";
import {
  getNotifications,
  markNotificationsRead,
  deleteNotification,
  clearAllNotifications,
} from "@/lib/problems/api";
import { cn } from "@/lib/utils";

const TYPE_ICONS: Record<string, React.ReactNode> = {
  submission: <CheckCircle2 className="size-4" />,
  contest_start: <Trophy className="size-4" />,
  contest_end: <Clock className="size-4" />,
  achievement: <Zap className="size-4" />,
  course: <BookOpen className="size-4" />,
  system: <Info className="size-4" />,
};

const TYPE_COLORS: Record<string, string> = {
  submission: "bg-emerald-100 text-emerald-600",
  contest_start: "bg-blue-100 text-blue-600",
  contest_end: "bg-amber-100 text-amber-600",
  achievement: "bg-purple-100 text-purple-600",
  course: "bg-cyan-100 text-cyan-600",
  system: "bg-neutral-100 text-neutral-600",
};

function relativeTime(ts: string): string {
  const then = new Date(ts).getTime();
  const now = Date.now();
  const sec = Math.floor((now - then) / 1000);
  if (sec < 10) return "Hozir";
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}s`;
  return `${Math.floor(hr / 24)}k`;
}

export function NotificationBell() {
  const { isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error, mutate } = useSWR(
    isAuthenticated ? "notifications" : null,
    () => getNotifications({ limit: 30 }),
    { refreshInterval: 30000, revalidateOnFocus: true }
  );

  useEffect(() => setMounted(true), []);

  // SSE: Real-time notification
  useSSEEvent("notification", (payload: NotificationPayload) => {
    mutate();
  });

  // Tashqariga bosilganda yopish
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const unreadCount = data?.unread_count || 0;

  const handleMarkRead = useCallback(
    async (e: React.MouseEvent, id: number) => {
      e.stopPropagation();
      try {
        await markNotificationsRead([id]);
        mutate();
      } catch (err) {
        console.error(err);
      }
    },
    [mutate]
  );

  const handleMarkAllRead = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      try {
        await markNotificationsRead();
        mutate();
      } catch (err) {
        console.error(err);
      }
    },
    [mutate]
  );

  const handleDelete = useCallback(
    async (e: React.MouseEvent, id: number) => {
      e.stopPropagation();
      try {
        await deleteNotification(id);
        mutate();
      } catch (err) {
        console.error(err);
      }
    },
    [mutate]
  );

  const handleClearAll = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      try {
        await clearAllNotifications();
        mutate();
      } catch (err) {
        console.error(err);
      }
    },
    [mutate]
  );

  if (!mounted || !isAuthenticated) return null;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "relative flex h-9 w-9 items-center justify-center rounded-lg text-neutral-500 transition-all",
          open
            ? "bg-orange-50 text-orange-600"
            : "hover:bg-neutral-100 hover:text-neutral-700"
        )}
        aria-label="Bildirishnomalar"
      >
        <Bell className={cn("size-[18px]", unreadCount > 0 && "fill-current")} />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] animate-in zoom-in items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white shadow-sm">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-96 overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-neutral-100 bg-gradient-to-r from-orange-50/50 to-white px-5 py-3.5">
            <div>
              <h3 className="text-sm font-bold text-neutral-900">
                Bildirishnomalar
              </h3>
              <p className="text-[11px] text-neutral-500">
                {unreadCount > 0
                  ? `${unreadCount} ta yangi xabar`
                  : "Barchasi o'qildi"}
              </p>
            </div>
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100"
                  title="Barchasini o'qilgan deb belgilash"
                >
                  <CheckCheck className="size-3.5" />
                  <span className="hidden sm:inline">O'qildi</span>
                </button>
              )}
              {data && data.count > 0 && (
                <button
                  onClick={handleClearAll}
                  className="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-red-50 hover:text-red-500"
                  title="Hammasini tozalash"
                >
                  <Trash2 className="size-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* List */}
          <div className="max-h-[28rem] overflow-y-auto">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center gap-2 py-12">
                <Loader2 className="size-6 animate-spin text-orange-400" />
                <p className="text-xs text-neutral-400">Yuklanmoqda...</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
                <XCircle className="size-8 text-red-300" />
                <p className="text-xs text-red-500">Yuklashda xatolik</p>
              </div>
            ) : !data || data.data.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-3 py-12 text-neutral-300">
                <div className="flex size-14 items-center justify-center rounded-full bg-neutral-50">
                  <Bell className="size-7 opacity-40" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-neutral-500">
                    Hali xabar yo'q
                  </p>
                  <p className="mt-0.5 text-[11px] text-neutral-400">
                    Yechim yuborganingizda natijalar shu yerda chiqadi
                  </p>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-neutral-50">
                {data.data.map((n) => (
                  <NotificationRow
                    key={n.id}
                    notification={n}
                    onMarkRead={handleMarkRead}
                    onDelete={handleDelete}
                    onClose={() => setOpen(false)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {data && data.count > 0 && (
            <div className="border-t border-neutral-100 bg-neutral-50/50 px-4 py-2.5 text-center">
              <Link
                href="/notifications"
                onClick={() => setOpen(false)}
                className="text-xs font-medium text-orange-600 transition-colors hover:text-orange-700"
              >
                Barcha bildirishnomalar →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NotificationRow({
  notification: n,
  onMarkRead,
  onDelete,
  onClose,
}: {
  notification: NotificationItem;
  onMarkRead: (e: React.MouseEvent, id: number) => void;
  onDelete: (e: React.MouseEvent, id: number) => void;
  onClose: () => void;
}) {
  const icon = TYPE_ICONS[n.type] || TYPE_ICONS.system;
  const colorClass = TYPE_COLORS[n.type] || TYPE_COLORS.system;

  const content = (
    <div
      className={cn(
        "group relative flex items-start gap-3 px-5 py-3.5 transition-colors",
        !n.is_read ? "bg-orange-50/30" : "hover:bg-neutral-50"
      )}
    >
      {/* Icon */}
      <span
        className={cn(
          "mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full",
          colorClass
        )}
      >
        {icon}
      </span>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p
            className={cn(
              "text-sm leading-snug",
              !n.is_read
                ? "font-semibold text-neutral-900"
                : "font-medium text-neutral-600"
            )}
          >
            {n.title}
          </p>
          <span className="shrink-0 text-[10px] tabular-nums text-neutral-400">
            {relativeTime(n.created_at)}
          </span>
        </div>
        <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-neutral-500">
          {n.message}
        </p>

        {/* Actions */}
        <div className="mt-2 flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
          {!n.is_read && (
            <button
              onClick={(e) => onMarkRead(e, n.id)}
              className="flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium text-orange-600 transition-colors hover:bg-orange-50"
            >
              <CheckCheck className="size-3" />
              O'qildi
            </button>
          )}
          <button
            onClick={(e) => onDelete(e, n.id)}
            className="flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium text-neutral-400 transition-colors hover:bg-red-50 hover:text-red-500"
          >
            <Trash2 className="size-3" />
            O'chirish
          </button>
        </div>
      </div>

      {/* Unread dot */}
      {!n.is_read && (
        <span className="absolute right-4 top-4 size-2 rounded-full bg-orange-500 ring-2 ring-white" />
      )}
    </div>
  );

  if (n.link) {
    return (
      <Link href={n.link} onClick={onClose} className="block">
        {content}
      </Link>
    );
  }

  return <div>{content}</div>;
}