import type { ProblemDetail } from "@/lib/problems/types";

export type LessonSelection =
  | { type: "lecture"; slug: string }
  | { type: "problem"; slug: string }
  | { type: "quiz"; id: number }
  | { type: "none" };

export interface LessonSummaryLecture {
  id: number;
  t: string;
  s: string;
  o: number;
  done: boolean;
}

export interface LessonSummaryProblem {
  id: number;
  t: string;
  s: string;
  xp: number;
  done: boolean;
}

export interface LessonSummaryQuiz {
  id: number;
  xp: number;
  done: boolean;
}

export interface LessonSummary {
  id?: number;
  t: string;
  s: string;
  tk: number;
  us: {
    ft: number;
  };
  lecs: LessonSummaryLecture[];
  probs: LessonSummaryProblem[];
  qs: LessonSummaryQuiz[];
}

export interface LectureDetail {
  id: number;
  title: string;
  slug: string;
  content: string;
  video?: {
    hls_url?: string;
    thumbnail?: string;
    duration?: number | string;
  } | null;
  is_completed: boolean;
  xp: number;
}

export interface QuizChoice {
  id: number;
  text: string;
}

export interface QuizDetail {
  id: number;
  question: string;
  choices: QuizChoice[];
  done: boolean;
  xp: number;
  video?: {
    hls_url?: string;
    thumbnail?: string;
    duration?: number | string;
  } | null;
}

export interface QuizCompleteResult {
  xp: number;
  ans: {
    id: number;
    correct: boolean;
  };
}

export type LessonProblemDetail = ProblemDetail;

export function resolveInitialSelection(
  lesson: LessonSummary,
  sp?: { tab?: string; ref?: string }
): LessonSelection {
  if (sp?.tab === "lecture" && sp?.ref) {
    return { type: "lecture", slug: sp.ref };
  }
  if (sp?.tab === "problem" && sp?.ref) {
    return { type: "problem", slug: sp.ref };
  }
  if (sp?.tab === "quiz" && sp?.ref) {
    return { type: "quiz", id: Number(sp.ref) };
  }
  if (lesson.lecs.length > 0) {
    return { type: "lecture", slug: lesson.lecs[0].s };
  }
  if (lesson.probs.length > 0) {
    return { type: "problem", slug: lesson.probs[0].s };
  }
  if (lesson.qs.length > 0) {
    return { type: "quiz", id: lesson.qs[0].id };
  }
  return { type: "none" };
}

export function selectionToSearchParams(
  sel: LessonSelection
): Record<string, string> {
  if (sel.type === "lecture") return { tab: "lecture", ref: sel.slug };
  if (sel.type === "problem") return { tab: "problem", ref: sel.slug };
  if (sel.type === "quiz") return { tab: "quiz", ref: String(sel.id) };
  return {};
}
