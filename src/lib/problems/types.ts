export interface Category {
  id: number;
  name: string;
  slug?: string;
}

export interface Tag {
  id: number;
  name: string;
  slug?: string;
}

export interface TestCase {
  id?: number;
  input: string;
  output: string;
  is_sample?: boolean;
}

export interface ProblemDetail {
  id: number;
  slug: string;
  title: string;
  desc: string;
  dif: string;
  difficulty?: string;
  xp: number;
  time_l: number;
  memory_l: number;
  cate_name?: string;
  category?: string;
  solved?: boolean;
  tags: Tag[];
  hints: (string | { id?: number; text?: string; content?: string })[];
  chall: (string | { id?: number; title?: string })[];
  exam: TestCase[];
  starter_codes?: Record<string, string>;
  default_code?: string;
  allowed_languages?: string[];
}

export interface Problems {
  id: number;
  slug: string;
  title: string;
  difficulty: string;
  dif?: string;
  category?: string;
  solved?: boolean;
  xp?: number;
  acceptance_rate?: number;
  submissions_count?: number;
}

export interface ProblemsSearchParams {
  page?: number;
  limit?: number;
  search?: string;
  difficulty?: string;
  category?: string;
  tag?: string;
  sort?: string;
  status?: string;
}

export interface ProblemsResponse {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: Problems[];
}

export interface ProblemStats {
  total: number;
  solved: number;
  by_difficulty?: Record<string, { total: number; solved: number }>;
}

export interface RunResultItem {
  test_case: number;
  input?: string;
  expected_output?: string;
  user_output?: string;
  status: string;
  time?: number;
  memory?: number;
  error?: string | null;
}

export interface RunResponse {
  status: string;
  results: RunResultItem[];
  compile_error?: string | null;
  runtime_error?: string | null;
}

export interface SubmissionTestResult {
  test_index: number;
  verdict: string;
  time: number;
  memory: number;
  input?: string;
  output?: string;
  expected?: string;
}

export interface SubmissionDetail {
  id: number;
  verdict: string;
  verdict_display?: string;
  code: string;
  language: string;
  time: number;
  memory: number;
  submitted_at: string;
  problem: {
    title: string;
    slug: string;
  };
  tests?: SubmissionTestResult[];
  test_results?: SubmissionTestResult[];
  error_message?: string | null;
}

export interface ProblemSubmissionsResponse {
  results: {
    id: number;
    verdict: string;
    verdict_display: string;
    language: string;
    time: number;
    memory: number;
    submitted_at: string;
  }[];
}
