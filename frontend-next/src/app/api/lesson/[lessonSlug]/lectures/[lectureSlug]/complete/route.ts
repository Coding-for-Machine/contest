import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function POST(
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

  const response = await ApiProxy.post(
    `/courses/lesson/${lessonSlug}/lectures/${lectureSlug}/complete/`,
    {},
    {
      withAuth: true,
    }
  );

  return NextResponse.json(response.data, {
    status: response.status,
  });
}