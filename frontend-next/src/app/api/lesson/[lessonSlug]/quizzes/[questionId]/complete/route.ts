import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function POST(
  req: Request,
  {
    params,
  }: {
    params: Promise<{
      lessonSlug: string;
      questionId: string;
    }>;
  }
) {
  const { lessonSlug, questionId } = await params;

  const body = await req.json();

  const response = await ApiProxy.post(
    `/courses/lesson/${lessonSlug}/quizzes/${questionId}/complete/`,
    {
      choice_id: body.choice_id,
    },
    {
      withAuth: true,
    }
  );

  return NextResponse.json(response.data, {
    status: response.status,
  });
}