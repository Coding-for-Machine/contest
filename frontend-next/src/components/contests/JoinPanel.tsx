"use client";

import { useState } from "react";
import { Calendar, Clock, Users, Percent, ShieldAlert, KeyRound } from "lucide-react";
import { Contest } from "@/lib/contests/types";
import { formatDateUz } from "@/lib/contests/utils";
import { MOCK_ACCESS_KEY } from "@/lib/contests/mock-data";

function Row({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Calendar;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between py-2.5 text-sm">
      <span className="flex items-center gap-2 text-[#8A8677]">
        <Icon size={15} strokeWidth={1.75} aria-hidden />
        {label}
      </span>
      <span className="font-medium text-[#121212]">{value}</span>
    </div>
  );
}

export function JoinPanel({ contest }: { contest: Contest }) {
  const [key, setKey] = useState("");
  const [unlocked, setUnlocked] = useState(contest.type === "open");
  const [error, setError] = useState("");

  const deadline = contest.registration_deadline ?? contest.start_time;
  const registrationOpen =
    contest.status === "upcoming" && new Date() <= new Date(deadline);

  function handleUnlock(e: React.FormEvent) {
    e.preventDefault();
    if (key.trim() === MOCK_ACCESS_KEY) {
      setUnlocked(true);
      setError("");
    } else {
      setError("Kalit noto'g'ri. Qaytadan urinib ko'ring.");
    }
  }

  const ctaLabel =
    contest.status === "ended"
      ? "Natijalarni ko'rish"
      : contest.status === "ongoing"
        ? "Testni boshlash"
        : registrationOpen
          ? "Ro'yxatdan o'tish"
          : "Ro'yxat yopilgan";

  const ctaDisabled = contest.status === "upcoming" && !registrationOpen;

  return (
    <div className="sticky top-6 rounded-xl border border-[#E4E1D9] bg-white p-5">
      <div className="divide-y divide-[#EFEDE6]">
        <Row icon={Calendar} label="Boshlanishi" value={formatDateUz(contest.start_time)} />
        <Row icon={Clock} label="Tugashi" value={formatDateUz(contest.end_time)} />
        <Row
          icon={Percent}
          label="O'tish balli"
          value={`${contest.pass_score_percent}%`}
        />
        <Row
          icon={ShieldAlert}
          label="Jarima koeffitsiyenti"
          value={`${Math.round(contest.penalty_coefficient * 100)}%`}
        />
        <Row
          icon={Users}
          label="Ishtirokchilar"
          value={
            contest.max_participants > 0
              ? `${contest.participants_count} / ${contest.max_participants}`
              : `${contest.participants_count}`
          }
        />
      </div>

      {contest.type === "private" && !unlocked ? (
        <form onSubmit={handleUnlock} className="mt-4 space-y-2">
          <label className="flex items-center gap-1.5 text-xs text-[#8A8677]">
            <KeyRound size={13} strokeWidth={1.75} aria-hidden />
            Kirish kaliti
          </label>
          <input
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Kalitni kiriting"
            className="w-full rounded-lg border border-[#E4E1D9] px-3 py-2 text-sm outline-none focus:border-[#121212]"
          />
          {error && <p className="text-xs text-[#B23A3A]">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-lg bg-[#121212] px-4 py-2.5 text-sm font-medium text-white hover:opacity-90"
          >
            Kirish
          </button>
        </form>
      ) : (
        <button
          disabled={ctaDisabled}
          className="mt-4 w-full rounded-lg bg-[#121212] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-[#E4E1D9] disabled:text-[#8A8677]"
        >
          {ctaLabel}
        </button>
      )}
    </div>
  );
}