export interface ApiError {
  status: number;
  message: string;
  detail?: any;
}

export interface SessionChoice {
  id: number;
  text: string;
}

export interface SessionQuestion {
  id: number;
  text: string;
  choices: SessionChoice[];
  image?: string | null;
  type?: string;
}

export interface TestDetail {
  id: number;
  title: string;
  slug: string;
  desc?: string;
  description?: string;
  start?: string | null;
  end?: string | null;
  price?: number;
  duration_minutes?: number;
  max_att?: number;
  user?: {
    status: "in_progress" | "completed" | "not_started" | string;
    count: number;
  } | null;
  total_questions?: number;
  passing_score?: number;
  video?: {
    hls_url?: string;
    thumbnail?: string;
    duration?: number | string;
  } | null;
}

export interface TestSessionHistoryItem {
  id: number;
  session_id?: number | string;
  created_at: string;
  finished_at?: string | null;
  status: "completed" | "in_progress" | "expired" | string;
  score?: number;
  total_questions?: number;
  correct_count?: number;
  percentage?: number;
}

export interface TestSessionHistoryResponse {
  sessions?: TestSessionHistoryItem[];
  results?: TestSessionHistoryItem[];
}

export interface StartSessionResponse {
  session_id: number | string;
  test_title: string;
  questions: SessionQuestion[];
  duration_minutes: number;
  expires_at: string;
  lifelines?: number;
}

export interface SessionQuestionsResponse {
  questions: SessionQuestion[];
}

export interface SessionStatusResponse {
  remaining_seconds: number;
  status: string;
}

export interface FinishResponse {
  session_id: number | string;
  score: number;
  total_questions: number;
  correct_answers: number;
  passed: boolean;
  passed_score?: number;
  results?: any[];
}

export interface LifelineResponse {
  eliminated_choice_ids: number[];
  lifelines_left: number;
}
