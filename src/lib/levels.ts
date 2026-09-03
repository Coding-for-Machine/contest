export type CertificateSourceType = "course" | "contest" | "exam" | "special";

export const SOURCE_TYPE_LABELS: Record<CertificateSourceType, string> = {
  course: "Kurs",
  contest: "Musobaqa",
  exam: "Imtihon",
  special: "Maxsus",
};

export function levelLabel(level: string): string {
  const map: Record<string, string> = {
    beginner: "Boshlang'ich",
    bronze: "Bronza",
    silver: "Kumush",
    gold: "Oltin",
    platinum: "Platina",
    diamond: "Olmos",
    master: "Usta",
    grandmaster: "Grossmeyster",
  };
  return map[level.toLowerCase()] ?? level;
}

export function levelBadgeClass(level: string): string {
  const map: Record<string, string> = {
    beginner: "bg-slate-500/10 text-slate-300 border-slate-700",
    bronze: "bg-amber-700/10 text-amber-500 border-amber-800",
    silver: "bg-slate-300/10 text-slate-300 border-slate-500",
    gold: "bg-yellow-500/10 text-yellow-400 border-yellow-600",
    platinum: "bg-emerald-500/10 text-emerald-400 border-emerald-600",
    diamond: "bg-cyan-500/10 text-cyan-400 border-cyan-600",
    master: "bg-purple-500/10 text-purple-400 border-purple-600",
    grandmaster: "bg-red-500/10 text-red-400 border-red-600",
  };
  return map[level.toLowerCase()] ?? "bg-slate-500/10 text-slate-300 border-slate-700";
}
