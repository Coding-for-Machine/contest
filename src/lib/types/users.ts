export interface ActivityItem {
  id: number | string;
  type: "submission" | "test" | "contest";
  title: string;
  timestamp: string;
  verdict?: string;
  verdict_display?: string;
  xp?: number;
  rank?: number;
}

export interface ActivityResponse {
  activity: ActivityItem[];
}

export interface CertificateItem {
  id: number;
  source_type: string;
  source_title: string;
  certificate_code: string;
  issued_at: string;
  verify_url: string;
  pdf_url?: string | null;
}

export interface CertificatesResponse {
  certificates: CertificateItem[];
}

export interface UserCourseItem {
  course: {
    id: number;
    title: string;
    slug: string;
  };
  is_completed: boolean;
  progress_percent: number;
  finished_lessons: number;
  total_lessons: number;
  finished_tests: number;
  total_tests: number;
}

export interface UserCoursesResponse {
  courses: UserCourseItem[];
}

export interface HistoryItem {
  id: number;
  problem: {
    title: string;
    slug?: string;
  };
  verdict: string;
  verdict_display: string;
  language?: string;
  submitted_at: string;
  progress?: string;
}

export interface HistoryResponse {
  results: HistoryItem[];
}
