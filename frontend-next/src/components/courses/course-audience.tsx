"use client";

import { useState } from "react";
import { CheckCircle2, HelpCircle } from "lucide-react";
import type { CourseAudienceData } from "@/lib/data/course-audiences";

interface CourseAudienceProps {
  data: CourseAudienceData;
}

export function CourseAudience({ data }: CourseAudienceProps) {
  const [active, setActive] = useState(data.defaultTab);
  const current = data.tabs.find((t) => t.id === active)!;

  return (
    <section id="audience">
      <div className="mb-6 flex items-baseline gap-3">
        <span className="font-mono text-xs text-[#D9AE55]">## audience</span>
        <h2 className="font-display text-2xl font-bold tracking-tight text-white">
          Kurs kim uchun?
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {data.tabs.map((tab) => {
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className={`flex flex-col items-start gap-3 rounded-lg border p-5 text-left transition ${
                isActive
                  ? "border-[#D9AE55]/50 bg-[#1a1a1a]"
                  : "border-white/10 bg-[#121212] hover:border-white/20"
              }`}
            >
              <span className={`text-sm font-bold ${isActive ? "text-[#D9AE55]" : "text-white/50"}`}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-4 rounded-lg border border-white/10 bg-[#121212] p-6">
        <ul className="flex flex-col gap-3">
          {current.features.map((feature, idx) => (
            <li key={idx} className="flex items-start gap-3 text-sm text-white/60">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[#D9AE55]" />
              {feature}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}