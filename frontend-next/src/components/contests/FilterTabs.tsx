"use client";

import { cn } from "@/lib/utils";

const options = [
  { value: "all", label: "Hammasi" },
  { value: "ongoing", label: "Jonli" },
  { value: "upcoming", label: "Kutilmoqda" },
  { value: "ended", label: "Yakunlangan" },
] as const;

export type FilterValue = (typeof options)[number]["value"];

export function FilterTabs({
  value,
  onChange,
}: {
  value: FilterValue;
  onChange: (v: FilterValue) => void;
}) {
  return (
    <div className="flex gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-full px-3.5 py-1.5 text-sm transition-colors",
            value === opt.value
              ? "bg-[#121212] text-white"
              : "text-[#8A8677] hover:bg-[#F5F4EF]"
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}