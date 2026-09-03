import { Contest } from "./types";

export const MOCK_ACCESS_KEY = "CFM2025";

export const contests: Contest[] = [
  {
    id: 1,
    title: "CfM Contest #1: Bahoriy Dasturlash Musobaqasi",
    slug: "cfm-spring-contest-2025",
    description: "Algoritmlar va ma'lumotlar tuzilmalari bo'yicha yillik bahoriy musobaqa. O'zingizni sinab ko'ring va qimmatbaho sovg'alarga ega bo'ling!",
    status: "ongoing",
    type: "open",
    start_time: new Date(Date.now() - 3600 * 1000).toISOString(),
    end_time: new Date(Date.now() + 86400 * 1000 * 2).toISOString(),
    duration_minutes: 120,
    registration_deadline: new Date(Date.now() + 86400 * 1000).toISOString(),
    questions_count: 5,
    pass_score_percent: 60,
    penalty_coefficient: 0.1,
    participants_count: 142,
    cover_image: "/cfm_logo.webp",
    intro_video: null,
    prizes: [
      { id: 1, rank_target: 1, title: "MacBook Air M2", description: "Bosh sovrin" },
      { id: 2, rank_target: 2, title: "iPad 10th Gen", description: "2-o'rin uchun" },
      { id: 3, rank_target: 3, title: "AirPods Pro", description: "3-o'rin uchun" },
    ],
    leaderboard: [
      { id: 1, rank: 1, display_name: "nodir_coder", accuracy_percent: 98, total_xp_earned: 950 },
      { id: 2, rank: 2, display_name: "dilshod_dev", accuracy_percent: 92, total_xp_earned: 880 },
      { id: 3, rank: 3, display_name: "aziza_algo", accuracy_percent: 88, total_xp_earned: 820 },
    ],
  },
  {
    id: 2,
    title: "CfM Junior Cup: Yangi Boshlovchilar Uchun",
    slug: "cfm-junior-cup-2025",
    description: "Dasturlashni endi boshlaganlar uchun maxsus saralash bosqichi. Qiziqarli masalalar va sovrinlar!",
    status: "upcoming",
    type: "open",
    start_time: new Date(Date.now() + 86400 * 1000 * 5).toISOString(),
    end_time: new Date(Date.now() + 86400 * 1000 * 6).toISOString(),
    duration_minutes: 90,
    registration_deadline: new Date(Date.now() + 86400 * 1000 * 4).toISOString(),
    questions_count: 4,
    pass_score_percent: 50,
    penalty_coefficient: 0.05,
    participants_count: 85,
    cover_image: "/cfm_logo.webp",
    intro_video: null,
    prizes: [
      { id: 4, rank_target: 1, title: "Keychron Mexanik Klaviatura", description: "1-o'rin" },
      { id: 5, rank_target: 2, title: "Logitech MX Master Sichqoncha", description: "2-o'rin" },
      { id: 6, rank_target: 3, title: "CfM Premium Kurs Obunasi", description: "3-o'rin" },
    ],
    leaderboard: [],
  },
];

export function getContestBySlug(slug: string): Contest | undefined {
  return contests.find((c) => c.slug === slug) ?? contests[0];
}

export function getFeaturedContest(): Contest {
  return contests[0];
}
