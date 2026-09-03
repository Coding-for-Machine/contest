import ApiProxy from "@/app/api/proxy";
import type {
  LessonSummary,
  LectureDetail,
  LessonProblemDetail,
  QuizDetail,
} from "./types";

const MOCK_LESSON_SUMMARY: LessonSummary = {
  id: 1,
  t: "1-Dars: Kirish va O'zgaruvchilar",
  s: "kirish-va-ozgaruvchilar",
  tk: 4,
  us: {
    ft: 1,
  },
  lecs: [
    {
      id: 1,
      t: "O'zgaruvchilar va tiplar",
      s: "ozgaruvchilar-va-tiplar",
      o: 1,
      done: true,
    },
  ],
  probs: [
    {
      id: 1,
      t: "Ikki son yig'indisi",
      s: "ikki-son-yigindisi",
      xp: 30,
      done: false,
    },
    {
      id: 2,
      t: "Kvadrat yuzi",
      s: "kvadrat-yuzi",
      xp: 20,
      done: false,
    },
  ],
  qs: [
    {
      id: 1,
      xp: 25,
      done: false,
    },
  ],
};

export async function getLessonSummary(
  lessonSlug: string
): Promise<LessonSummary | null> {
  try {
    const res = await ApiProxy.get<LessonSummary>(
      `/courses/lesson/${lessonSlug}/summary`,
      { cache: "no-store" }
    );
    if (res.data) return res.data;
  } catch {
    // fallback
  }

  return {
    ...MOCK_LESSON_SUMMARY,
    s: lessonSlug,
  };
}

export async function getLessonLecture(
  lessonSlug: string,
  lectureSlug: string
): Promise<LectureDetail | null> {
  try {
    const res = await ApiProxy.get<LectureDetail>(
      `/courses/lesson/${lessonSlug}/lecture/${lectureSlug}`,
      { cache: "no-store" }
    );
    if (res.data) return res.data;
  } catch {
    // fallback
  }

  return {
    id: 1,
    title: "O'zgaruvchilar va tiplar",
    slug: lectureSlug,
    content: `# O'zgaruvchilar va tiplar

Python dasturlash tilida ma'lumotlar turlari juda muhim rol o'ynaydi:

- **int**: Butun sonlar (1, 2, -5)
- **float**: Haqiqiy sonlar (3.14, 2.718)
- **str**: Matnli ma'lumotlar ("Salom dunyo")
- **bool**: Mantiqiy qiymatlar (True, False)

\`\`\`python
a = 10
b = 20
print(a + b)
\`\`\`
`,
    video: null,
    is_completed: true,
    xp: 20,
  };
}

export async function getLessonProblem(
  lessonSlug: string,
  problemSlug: string
): Promise<LessonProblemDetail | null> {
  try {
    const res = await ApiProxy.get<LessonProblemDetail>(
      `/courses/lesson/${lessonSlug}/problem/${problemSlug}`,
      { cache: "no-store" }
    );
    if (res.data) return res.data;
  } catch {
    // fallback
  }

  return {
    id: 101,
    slug: problemSlug,
    title: "Ikki son yig'indisi",
    desc: "Berilgan ikkita butun son `a` va `b` ning yig'indisini hisoblang.",
    dif: "easy",
    difficulty: "easy",
    xp: 30,
    time_l: 1.0,
    memory_l: 256,
    cate_name: "Asoslar",
    solved: false,
    tags: [{ id: 1, name: "Asoslar" }],
    hints: ["Standart kiruvchi ma'lumotlarni o'qing va qo'shing."],
    chall: [],
    exam: [
      { id: 1, input: "2 3", output: "5", is_sample: true },
      { id: 2, input: "10 -2", output: "8", is_sample: true },
    ],
    starter_codes: {
      python: "import sys\n\ndef main():\n    line = sys.stdin.read().split()\n    if line:\n        a, b = map(int, line[:2])\n        print(a + b)\n\nif __name__ == '__main__':\n    main()",
    },
    default_code: "import sys\n\ndef main():\n    line = sys.stdin.read().split()\n    if line:\n        a, b = map(int, line[:2])\n        print(a + b)\n\nif __name__ == '__main__':\n    main()",
    allowed_languages: ["python", "javascript", "cpp"],
  };
}

export async function getLessonQuiz(
  lessonSlug: string,
  quizId: number
): Promise<QuizDetail | null> {
  try {
    const res = await ApiProxy.get<QuizDetail>(
      `/courses/lesson/${lessonSlug}/quiz/${quizId}`,
      { cache: "no-store" }
    );
    if (res.data) return res.data;
  } catch {
    // fallback
  }

  return {
    id: quizId,
    question: "Python dasturlash tilida qaysi kalit so'z funksiyalarni e'lon qilish uchun ishlatiladi?",
    choices: [
      { id: 1, text: "def" },
      { id: 2, text: "func" },
      { id: 3, text: "function" },
      { id: 4, text: "lambda" },
    ],
    done: false,
    xp: 25,
    video: null,
  };
}
