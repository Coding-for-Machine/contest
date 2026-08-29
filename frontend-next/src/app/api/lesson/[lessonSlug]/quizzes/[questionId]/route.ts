import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
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

  const response = await ApiProxy.get(
    `/courses/lesson/${lessonSlug}/quizzes/${questionId}/`, {
    withAuth: true,
  }
  );

  return NextResponse.json(response.data, {
    status: response.status,
  });
}