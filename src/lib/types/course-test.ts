export interface TestQuestionChoice {
  id: number;
  text: string;
}

export interface TestQuestion {
  id: number;
  question_text: string;
  choices: TestQuestionChoice[];
}

export interface TestInfo {
  id: number;
  title: string;
  description?: string;
  duration_minutes: number;
  question_count: number;
  min_pass_percentage: number;
  video?: {
    thumbnail?: string;
  } | null;
  best_result?: {
    correct: number;
    xp: number;
  } | null;
}

export interface TestFinishResponse {
  correct: number;
  wrong: number;
  unanswered: number;
  earned_xp?: number;
  passed?: boolean;
}

export interface StartTestSessionResponse {
  session_id: string;
  questions: TestQuestion[];
  duration_minutes: number;
}
