import type {
  Problems,
  ProblemsResponse,
  RunResponse,
  SubmissionDetail,
} from "./types";

export interface NotificationItem {
  id: number;
  type: string;
  title: string;
  message: string;
  created_at: string;
  is_read: boolean;
  link?: string | null;
}

export interface NotificationsResponse {
  count: number;
  unread_count: number;
  data: NotificationItem[];
}

export async function getProblemsList(params?: {
  offset?: number;
  limit?: number;
  search?: string;
  difficulty?: string;
  category?: string;
}): Promise<ProblemsResponse> {
  const query = new URLSearchParams();
  if (params?.offset) query.set("offset", String(params.offset));
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.search) query.set("search", params.search);
  if (params?.difficulty) query.set("difficulty", params.difficulty);
  if (params?.category) query.set("category", params.category);

  try {
    const res = await fetch(`/api/problems?${query.toString()}`);
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }

  const mockList: Problems[] = [
    {
      id: 1,
      slug: "two-sum",
      title: "Ikki son yig'indisi",
      difficulty: "easy",
      dif: "easy",
      category: "Massivlar va Xesh",
      solved: false,
      xp: 50,
      acceptance_rate: 68,
      submissions_count: 1240,
    },
    {
      id: 2,
      slug: "valid-palindrome",
      title: "Palindrom satr",
      difficulty: "easy",
      dif: "easy",
      category: "Satrlar",
      solved: true,
      xp: 40,
      acceptance_rate: 74,
      submissions_count: 980,
    },
    {
      id: 3,
      slug: "reverse-linked-list",
      title: "Bog'langan ro'yxatni teskari aylantirish",
      difficulty: "medium",
      dif: "medium",
      category: "Bog'langan ro'yxatlar",
      solved: false,
      xp: 80,
      acceptance_rate: 55,
      submissions_count: 810,
    },
    {
      id: 4,
      slug: "binary-tree-inorder",
      title: "Ikkilik daraxtni aylanib chiqish (Inorder)",
      difficulty: "medium",
      dif: "medium",
      category: "Daraxtlar",
      solved: false,
      xp: 85,
      acceptance_rate: 52,
      submissions_count: 670,
    },
    {
      id: 5,
      slug: "trapping-rain-water",
      title: "Yomg'ir suvini yig'ish",
      difficulty: "hard",
      dif: "hard",
      category: "Dinamik Dasturlash",
      solved: false,
      xp: 150,
      acceptance_rate: 34,
      submissions_count: 420,
    },
  ];

  return {
    count: mockList.length,
    results: mockList,
  };
}

export async function getSolutionVideo(slug: string): Promise<{
  hls_url: string;
  thumbnail: string | null;
  duration: number | null;
}> {
  try {
    const res = await fetch(`/api/problems/${slug}/video`);
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return {
    hls_url: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
    thumbnail: "/cfm_logo.webp",
    duration: 640,
  };
}

export async function getAdjacentProblem(
  slug: string,
  direction: "prev" | "next"
): Promise<{ slug: string } | null> {
  try {
    const res = await fetch(`/api/problems/${slug}/adjacent?dir=${direction}`);
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return { slug: direction === "next" ? "valid-palindrome" : "two-sum" };
}

export async function getRandomProblem(): Promise<{ slug: string }> {
  try {
    const res = await fetch("/api/problems/random");
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return { slug: "two-sum" };
}

export async function runCode(payload: {
  slug: string;
  language: string;
  code: string;
  custom_input?: string;
}): Promise<RunResponse> {
  try {
    const res = await fetch(`/api/problems/${payload.slug}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }

  return {
    status: "AC",
    results: [
      {
        test_case: 1,
        input: "[2, 7, 11, 15]\n9",
        expected_output: "[0, 1]",
        user_output: "[0, 1]",
        status: "AC",
        time: 0.04,
        memory: 14.2,
      },
      {
        test_case: 2,
        input: "[3, 2, 4]\n6",
        expected_output: "[1, 2]",
        user_output: "[1, 2]",
        status: "AC",
        time: 0.05,
        memory: 14.3,
      },
    ],
  };
}

export async function submitCode(payload: {
  slug: string;
  language: string;
  code: string;
}): Promise<{ submission_id: number | string }> {
  try {
    const res = await fetch(`/api/problems/${payload.slug}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return { submission_id: Date.now() };
}

export async function getSubmissionDetail(
  id: number | string
): Promise<SubmissionDetail> {
  try {
    const res = await fetch(`/api/user/submissions/${id}`);
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }

  return {
    id: Number(id),
    verdict: "AC",
    verdict_display: "Accepted",
    code: "def twoSum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        diff = target - n\n        if diff in seen:\n            return [seen[diff], i]\n        seen[n] = i\n    return []",
    language: "python",
    time: 0.04,
    memory: 14.2,
    submitted_at: new Date().toISOString(),
    problem: {
      title: "Ikki son yig'indisi",
      slug: "two-sum",
    },
    tests: [
      {
        test_index: 1,
        verdict: "AC",
        time: 0.04,
        memory: 14.2,
      },
      {
        test_index: 2,
        verdict: "AC",
        time: 0.05,
        memory: 14.3,
      },
    ],
  };
}

export async function getNotifications(params?: {
  limit?: number;
}): Promise<NotificationsResponse> {
  try {
    const res = await fetch(`/api/notifications?limit=${params?.limit ?? 20}`);
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return {
    count: 2,
    unread_count: 1,
    data: [
      {
        id: 1,
        type: "submission",
        title: "Taqdimot qabul qilindi!",
        message: "Ikki son yig'indisi masalasiga yuborgan yechimingiz muvaffaqiyatli o'tdi (+50 XP).",
        created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
        is_read: false,
      },
      {
        id: 2,
        type: "system",
        title: "Platformaga xush kelibsiz!",
        message: "CfM Contest platformasida musobaqalar va masalalarni yechishni boshlang.",
        created_at: new Date(Date.now() - 1000 * 3600 * 24).toISOString(),
        is_read: true,
      },
    ],
  };
}

export async function markNotificationsRead(ids?: number[]): Promise<void> {
  try {
    await fetch("/api/notifications/read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
  } catch {
    // ignore
  }
}

export async function deleteNotification(id: number): Promise<void> {
  try {
    await fetch(`/api/notifications/${id}`, { method: "DELETE" });
  } catch {
    // ignore
  }
}

export async function clearAllNotifications(): Promise<void> {
  try {
    await fetch("/api/notifications/clear", { method: "POST" });
  } catch {
    // ignore
  }
}
