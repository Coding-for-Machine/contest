import ApiProxy from "@/app/api/proxy";
import type { CourseDetail, CourseListItem, CourseHeroData } from "@/lib/types/course";
import type { TestInfo } from "@/lib/types/course-test";

const MOCK_HERO: CourseHeroData = {
  id: 1,
  title: "Python va Algoritmlar Asoslari",
  slug: "python-algoritmlar-asoslari",
  description: "Noldan professional darajagacha algoritmlar va ma'lumotlar tuzilmalarini Python tilida o'rganing. Texnik intervyularga to'liq tayyorgarlik.",
  price: 0,
  discount_price: null,
  thumbnail: "/cfm_logo.webp",
  total_lessons: 24,
  total_tests: 6,
  total_modules: 4,
  students: 1540,
  students_count: 1540,
  level: "beginner",
  video: {
    thumbnail: "/cfm_logo.webp",
  },
  modules: [
    {
      id: 10,
      title: "1-Modul: Python Sintaksisi va Asosiy Tushunchalar",
      order: 1,
      total_lessons: 6,
      total_tests: 1,
      lessons: [
        {
          id: 101,
          title: "Kirish va O'zgaruvchilar",
          slug: "kirish-va-ozgaruvchilar",
          order: 1,
          total_tasks: 3,
        },
        {
          id: 102,
          title: "Shart Operatolari va Sikllar",
          slug: "shart-operatorlari-va-sikllar",
          order: 2,
          total_tasks: 4,
        },
      ],
      test: {
        id: 1,
        title: "1-Modul Yakuniy Testi",
        slug: "1-modul-yakuniy-testi",
        total_questions: 10,
        passing_score: 70,
      },
    },
  ],
};

const MOCK_COURSES: CourseListItem[] = [
  MOCK_HERO,
  {
    id: 2,
    title: "Ma'lumotlar Tuzilmalari Chuqurlashtirilgan",
    slug: "malumotlar-tuzilmalari-chuqurlashtirilgan",
    description: "Bog'langan ro'yxatlar, daraxtlar, graflar va xesh-jadvallar. Har bir tuzilmaning amaliy tadbiqi.",
    price: 150000,
    discount_price: 99000,
    thumbnail: "/cfm_logo.webp",
    total_lessons: 32,
    total_tests: 8,
    total_modules: 5,
    students: 820,
    level: "intermediate",
  },
  {
    id: 3,
    title: "Dinamik Dasturlash (DP) Master-Klass",
    slug: "dinamik-dasturlash-master-klass",
    description: "Murakkab optimallashtirish masalalarini DP yordamida yechish uslublari.",
    price: 200000,
    discount_price: null,
    thumbnail: "/cfm_logo.webp",
    total_lessons: 18,
    total_tests: 4,
    total_modules: 3,
    students: 450,
    level: "advanced",
  },
];

export async function getCourseList(): Promise<CourseListItem[]> {
  try {
    const res = await ApiProxy.get<CourseListItem[]>("/courses", {
      cache: "no-store",
    });
    if (res.data && Array.isArray(res.data)) return res.data;
  } catch {
    // fallback
  }
  return MOCK_COURSES;
}

export async function getHeroCourse(): Promise<CourseHeroData | null> {
  try {
    const res = await ApiProxy.get<CourseHeroData>("/courses/hero", {
      cache: "no-store",
    });
    if (res.data) return res.data;
  } catch {
    // fallback
  }
  return MOCK_HERO;
}

export async function getCourseDetail(slug: string): Promise<CourseDetail | null> {
  try {
    const res = await ApiProxy.get<CourseDetail>(`/courses/${slug}`, {
      cache: "no-store",
    });
    if (res.data) return res.data;
  } catch {
    // fallback
  }

  if (slug === MOCK_HERO.slug) return MOCK_HERO;

  const found = MOCK_COURSES.find((c) => c.slug === slug);
  if (found) {
    return {
      ...found,
      modules: MOCK_HERO.modules,
      user_progress: null,
    };
  }

  return {
    ...MOCK_HERO,
    slug,
    title: slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  };
}

export async function getTestInfo(moduleId: number | string): Promise<TestInfo | null> {
  try {
    const res = await ApiProxy.get<TestInfo>(`/courses/module/${moduleId}/test/info`, {
      cache: "no-store",
    });
    if (res.data) return res.data;
  } catch {
    // fallback
  }

  return {
    test_id: Number(moduleId),
    title: "Modul Yakuniy Testi",
    total_questions: 10,
    duration_minutes: 20,
    passing_score: 70,
    max_attempts: 3,
    attempts_used: 0,
    can_start: true,
  };
}
