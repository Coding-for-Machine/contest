import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  req: NextRequest,
  {
    params,
  }: {
    params: Promise<{
      lessonSlug: string;
      problemSlug: string;
    }>;
  }
) {
  const { lessonSlug, problemSlug } = await params;

  const response = await ApiProxy.get(
    `/courses/lesson/${lessonSlug}/problem/${problemSlug}/`, {
    withAuth: true,
  }
  );

  return NextResponse.json(response.data, {
    status: response.status,
  });
}