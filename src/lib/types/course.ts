export type CourseLevel = "beginner" | "intermediate" | "advanced";

export interface CourseUserProgress {
  completed_lessons: number;
  completed_tests: number;
  progress_percent?: number;
  is_paid?: boolean;
}

export interface CourseModuleLesson {
  id: number;
  title: string;
  slug: string;
  order: number;
  is_locked?: boolean;
  is_completed?: boolean;
  is_in_progress?: boolean;
  total_tasks: number;
  finished_tasks?: number;
  user_status?: {
    is_completed: boolean;
    is_in_progress: boolean;
    finished_tasks: number;
  };
}

export interface CourseModuleTest {
  id: number;
  title: string;
  slug: string;
  passing_score?: number;
  total_questions?: number;
  user_status?: {
    is_completed: boolean;
    score?: number;
    passed?: boolean;
    attempts?: number;
  };
}

export interface CourseModule {
  id: number;
  title: string;
  slug?: string;
  order: number;
  locked?: boolean;
  total_lessons: number;
  total_tests: number;
  lessons: CourseModuleLesson[];
  test?: CourseModuleTest | null;
  user_status?: {
    completed_lessons: number;
    completed_tests: number;
    is_completed: boolean;
  };
}

export interface CourseListItem {
  id: number;
  title: string;
  slug: string;
  description?: string;
  price: number;
  discount_price?: number | null;
  thumbnail?: string | null;
  total_lessons: number;
  total_tests: number;
  is_paid?: boolean;
  is_completed?: boolean;
  students?: number;
  level?: CourseLevel;
  total_modules?: number;
}

export interface CourseDetail extends CourseListItem {
  video?: {
    hls_url?: string;
    thumbnail?: string;
    duration?: number | string;
  } | null;
  modules: CourseModule[];
  user_progress?: CourseUserProgress | null;
  audience?: string[];
  requirements?: string[];
  what_you_will_learn?: string[];
}

export interface CourseHeroData extends CourseDetail {
  students_count?: number;
}
