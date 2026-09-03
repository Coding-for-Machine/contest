import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import { ProblemDetail } from "@/lib/problems/types";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ lessonSlug: string; slug: string }> }
) {
  const { lessonSlug, slug } = await params;
  const { status, data } = await ApiProxy.get<ProblemDetail>(
    `/lesson/${lessonSlug}/problem/${slug}/`,
    { withAuth: true }
  );
  return NextResponse.json(data, { status });
}