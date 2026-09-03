export const DIFFICULTY_LABELS: Record<string | number, string> = {
  easy: "Oson",
  medium: "O'rta",
  hard: "Qiyin",
  EASY: "Oson",
  MEDIUM: "O'rta",
  HARD: "Qiyin",
  1: "Oson",
  2: "O'rta",
  3: "Qiyin",
  "1": "Oson",
  "2": "O'rta",
  "3": "Qiyin",
};

export const DIFFICULTY_CLASSES: Record<string | number, string> = {
  easy: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  hard: "bg-red-50 text-red-700 border-red-200",
  EASY: "bg-emerald-50 text-emerald-700 border-emerald-200",
  MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
  HARD: "bg-red-50 text-red-700 border-red-200",
  1: "bg-emerald-50 text-emerald-700 border-emerald-200",
  2: "bg-amber-50 text-amber-700 border-amber-200",
  3: "bg-red-50 text-red-700 border-red-200",
  "1": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "2": "bg-amber-50 text-amber-700 border-amber-200",
  "3": "bg-red-50 text-red-700 border-red-200",
};

export function toBase64(str: string): string {
  if (typeof window !== "undefined") {
    try {
      return btoa(unescape(encodeURIComponent(str)));
    } catch {
      return btoa(str);
    }
  }
  return Buffer.from(str, "utf-8").toString("base64");
}

export function formatMemory(kbOrBytes: number | null | undefined): string {
  if (kbOrBytes == null || isNaN(kbOrBytes)) return "—";
  if (kbOrBytes >= 1024 * 1024) return `${(kbOrBytes / (1024 * 1024)).toFixed(1)} GB`;
  if (kbOrBytes >= 1024) return `${(kbOrBytes / 1024).toFixed(1)} MB`;
  return `${kbOrBytes} KB`;
}

export function formatTime(secondsOrMs: number | null | undefined): string {
  if (secondsOrMs == null || isNaN(secondsOrMs)) return "—";
  if (secondsOrMs < 1) return `${Math.round(secondsOrMs * 1000)} ms`;
  return `${secondsOrMs.toFixed(2)} s`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("uz-UZ", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
