import { notFound } from "next/navigation";
import type { Metadata } from "next";

import {
  getLessonLecture,
  getLessonProblem,
  getLessonQuiz,
  getLessonSummary,
} from "@/lib/lesson/api.server";

import { resolveInitialSelection } from "@/lib/lesson/types";
import { LessonDetailShell } from "@/components/lesson/lesson-detail-shell";

import type {
  LessonSelection,
  LectureDetail,
  QuizDetail,
  LessonProblemDetail,
} from "@/lib/lesson/types";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface Props {
  params: Promise<{
    slug: string;
    lesson_slug: string;
  }>;
  searchParams: Promise<{
    tab?: string;
    ref?: string;
  }>;
}

/* ------------------------------------------------------------------ */
/* Metadata                                                           */
/* ------------------------------------------------------------------ */

export async function generateMetadata({
  params,
}: Props): Promise<Metadata> {
  const { slug, lesson_slug } = await params;

  const lesson = await getLessonSummary(lesson_slug);

  if (!lesson) {
    return {
      title: "Dars topilmadi | CfM Contest",
      robots: {
        index: false,
      },
    };
  }

  return {
    title: `${lesson.t} | CfM Contest`,
    description: `${lesson.t} darsi: ${lesson.lecs.length} ta ma'ruza, ${lesson.probs.length} ta masala, ${lesson.qs.length} ta savol.`,
    alternates: {
      canonical: `/courses/${slug}/lesson/${lesson.s}`,
    },
    robots: {
      index: false,
      follow: true,
    },
  };
}

/* ------------------------------------------------------------------ */
/* Content union                                                     */
/* ------------------------------------------------------------------ */

type ContentUnion =
  | {
      type: "lecture";
      data: LectureDetail;
    }
  | {
      type: "problem";
      data: LessonProblemDetail;
    }
  | {
      type: "quiz";
      data: QuizDetail;
    }
  | {
      type: "none";
    };

/* ------------------------------------------------------------------ */
/* Strategies                                                         */
/* ------------------------------------------------------------------ */

type StrategyMap = {
  [K in Exclude<LessonSelection["type"], "none">]: (
    slug: string,
    sel: Extract<LessonSelection, { type: K }>
  ) => Promise<ContentUnion>;
};

const strategies: StrategyMap = {
  lecture: async (slug, sel) => {
    const data = await getLessonLecture(slug, sel.slug);

    return data
      ? {
          type: "lecture",
          data,
        }
      : {
          type: "none",
        };
  },

  problem: async (slug, sel) => {
    const data = await getLessonProblem(slug, sel.slug);

    return data
      ? {
          type: "problem",
          data,
        }
      : {
          type: "none",
        };
  },

  quiz: async (slug, sel) => {
    const data = await getLessonQuiz(slug, sel.id);

    return data
      ? {
          type: "quiz",
          data,
        }
      : {
          type: "none",
        };
  },
};

/* ------------------------------------------------------------------ */
/* Page                                                               */
/* ------------------------------------------------------------------ */

export default async function CourseLessonPage({
  params,
  searchParams,
}: Props) {
  const { slug: courseSlug, lesson_slug } = await params;
  const sp = await searchParams;

  /* 1. Dars summary */
  const lesson = await getLessonSummary(lesson_slug);

  if (!lesson) {
    notFound();
  }

  /* 2. URL'dan tab/ref ni olish */
  const selection = resolveInitialSelection(lesson, sp);

  /* 3. Birinchi kontentni serverda yuklash */
  const initialContent: ContentUnion =
    selection.type === "none"
      ? {
          type: "none",
        }
      : await strategies[selection.type](
          lesson_slug,
          selection as never
        );

  return (
    <main className="min-h-screen bg-white">
      <LessonDetailShell
        lessonSlug={lesson_slug}
        courseSlug={courseSlug}
        initialLesson={lesson}
        initialSelection={selection}
        initialContent={initialContent}
      />
    </main>
  );
}