import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  req: Request,
  {
    params,
  }: {
    params: Promise<{
      lessonSlug: string;
      lectureSlug: string;
    }>;
  }
) {
  const { lessonSlug, lectureSlug } = await params;

  const response = await ApiProxy.get(
    `/courses/lesson/${lessonSlug}/lectures/${lectureSlug}/`, {
    withAuth: true,
  }
  );

  return NextResponse.json(response.data, {
    status: response.status,
  });
}