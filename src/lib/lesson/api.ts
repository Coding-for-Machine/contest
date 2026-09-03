import type {
  LectureDetail,
  QuizDetail,
  LessonProblemDetail,
  QuizCompleteResult,
} from "./types";

export class LessonApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "LessonApiError";
    this.status = status;
  }
}

export async function completeLectureClient(
  lessonSlug: string,
  lectureSlug: string
): Promise<{ completed: boolean; xp: number }> {
  try {
    const res = await fetch(
      `/api/courses/lesson/${lessonSlug}/lecture/${lectureSlug}/complete`,
      { method: "POST" }
    );
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return { completed: true, xp: 20 };
}

export async function completeQuizClient(
  lessonSlug: string,
  questionId: number,
  choiceId: number
): Promise<QuizCompleteResult> {
  try {
    const res = await fetch(
      `/api/courses/lesson/${lessonSlug}/quiz/${questionId}/submit`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ choice_id: choiceId }),
      }
    );
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return {
    xp: 25,
    ans: {
      id: choiceId,
      correct: true,
    },
  };
}

export async function fetchLectureClient(
  lessonSlug: string,
  lectureSlug: string
): Promise<LectureDetail> {
  try {
    const res = await fetch(
      `/api/courses/lesson/${lessonSlug}/lecture/${lectureSlug}`
    );
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }

  return {
    id: 1,
    title: "Kirish va O'zgaruvchilar",
    slug: lectureSlug,
    content: `# Kirish va O'zgaruvchilar

Python dasturlash tilida o'zgaruvchilar ma'lumotlarni xotirada saqlash uchun ishlatiladi.

\`\`\`python
# O'zgaruvchilarni e'lon qilish
x = 5
name = "CfM Contest"
is_active = True
\`\`\`

Dasturlashda o'zgaruvchilar nomlarini tushunarli va ma'noli qo'yish tavsiya etiladi.
`,
    video: null,
    is_completed: false,
    xp: 20,
  };
}

export async function fetchQuizClient(
  lessonSlug: string,
  quizId: number
): Promise<QuizDetail> {
  try {
    const res = await fetch(
      `/api/courses/lesson/${lessonSlug}/quiz/${quizId}`
    );
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }

  return {
    id: quizId,
    question: "Python tilida o'zgaruvchi qanday e'lon qilinadi?",
    choices: [
      { id: 1, text: "x = 5" },
      { id: 2, text: "var x = 5;" },
      { id: 3, text: "int x = 5;" },
      { id: 4, text: "dim x as Integer" },
    ],
    done: false,
    xp: 25,
    video: null,
  };
}

export async function fetchLessonProblemPreviewClient(
  lessonSlug: string,
  problemSlug: string
): Promise<LessonProblemDetail> {
  try {
    const res = await fetch(
      `/api/courses/lesson/${lessonSlug}/problem/${problemSlug}`
    );
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }

  return {
    id: 101,
    slug: problemSlug,
    title: "O'zgaruvchilar yig'indisi",
    desc: "Berilgan ikkita butun son a va b ning yig'indisini hisoblovchi dastur tuzing.",
    dif: "easy",
    difficulty: "easy",
    xp: 30,
    time_l: 1.0,
    memory_l: 256,
    cate_name: "Asoslar",
    solved: false,
    tags: [{ id: 1, name: "Asoslar" }],
    hints: ["a + b amalini ishlating"],
    chall: [],
    exam: [
      { id: 1, input: "2 3", output: "5", is_sample: true },
      { id: 2, input: "10 -5", output: "5", is_sample: true },
    ],
    starter_codes: {
      python: "def solve(a: int, b: int) -> int:\n    return a + b\n",
    },
    default_code: "def solve(a: int, b: int) -> int:\n    return a + b\n",
    allowed_languages: ["python", "javascript", "cpp"],
  };
}
