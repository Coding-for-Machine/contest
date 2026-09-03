import { ContestPrize } from "@/lib/types";

export type ContestStatus = "upcoming" | "ongoing" | "ended";
export type ContestType = "open" | "closed" | "special";

export interface RegistrationPreview {
  id: number | string;
  rank?: number;
  display_name: string;
  accuracy_percent: number;
  total_xp_earned: number;
}

export interface ContestIntroVideo {
  hls_url?: string;
  thumbnail?: string;
  duration?: number | string;
}

export interface Contest {
  id: number;
  title: string;
  slug: string;
  description: string;
  status: ContestStatus;
  type: ContestType;
  start_time: string;
  end_time: string;
  duration_minutes?: number;
  registration_deadline?: string;
  questions_count: number;
  pass_score_percent: number;
  penalty_coefficient: number;
  participants_count: number;
  cover_image?: string | null;
  intro_video?: ContestIntroVideo | null;
  prizes: ContestPrize[];
  leaderboard?: RegistrationPreview[];
}
