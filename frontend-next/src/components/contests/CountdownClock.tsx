"use client";

import { useEffect, useState } from "react";
import { getRemaining } from "@/lib/contests/utils";

function pad(n: number) {
  return n.toString().padStart(2, "0");
}

export function CountdownClock({
  target,
  label,
}: {
  target: string;
  label: string;
}) {
  const [remaining, setRemaining] = useState(() => getRemaining(target));

  useEffect(() => {
    const id = setInterval(() => setRemaining(getRemaining(target)), 1000);
    return () => clearInterval(id);
  }, [target]);

  const cells = [
    { value: remaining.days, unit: "kun" },
    { value: remaining.hours, unit: "soat" },
    { value: remaining.minutes, unit: "daq" },
    { value: remaining.seconds, unit: "son" },
  ];

  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-[0.14em] text-white/45">{label}</p>
      <div className="flex gap-2">
        {cells.map((c, i) => (
          <div key={c.unit} className="flex items-center gap-2">
            <div className="flex flex-col items-center rounded-md border border-white/15 bg-white/5 px-3 py-2 min-w-[58px]">
              <span className="font-mono text-2xl tabular-nums text-[#D9AE55]">
                {pad(c.value)}
              </span>
              <span className="mt-0.5 text-[10px] text-white/40">{c.unit}</span>
            </div>
            {i < cells.length - 1 && (
              <span className="font-mono text-lg text-white/20">:</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}