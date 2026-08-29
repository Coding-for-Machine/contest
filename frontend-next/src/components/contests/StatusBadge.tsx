import { Lock, Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import { ContestStatus, ContestType } from "@/lib/contests/types";

const statusLabel: Record<ContestStatus, string> = {
  upcoming: "Kutilmoqda",
  ongoing: "Jonli",
  ended: "Yakunlangan",
};

export function StatusBadge({
  status,
  tone = "light",
}: {
  status: ContestStatus;
  tone?: "light" | "dark";
}) {
  if (status === "ongoing") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
          tone === "dark"
            ? "bg-white/10 text-[#E7C878]"
            : "bg-[#121212] text-white"
        )}
      >
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#D9AE55]/70" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#D9AE55]" />
        </span>
        {statusLabel[status]}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium",
        tone === "dark"
          ? "border-white/15 text-white/60"
          : status === "ended"
            ? "border-[#E4E1D9] text-[#8A8677]"
            : "border-[#E4E1D9] text-[#4A4739]"
      )}
    >
      {statusLabel[status]}
    </span>
  );
}

export function TypeTag({ type }: { type: ContestType }) {
  const Icon = type === "private" ? Lock : Globe;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-[#8A8677]">
      <Icon size={13} strokeWidth={1.75} aria-hidden />
      {type === "private" ? "Yopiq" : "Ochiq"}
    </span>
  );
}