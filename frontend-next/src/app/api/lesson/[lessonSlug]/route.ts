import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  req: Request,
  {
    params,
  }: {
    params: Promise<{
      lessonSlug: string;
    }>;
  }
) {
  const { lessonSlug } = await params;

  const response = await ApiProxy.get(
    `/courses/lesson/${lessonSlug}/`
  );

  return NextResponse.json(response.data, {
    status: response.status,
  });
}