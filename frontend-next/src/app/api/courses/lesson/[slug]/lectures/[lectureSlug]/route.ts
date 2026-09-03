import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import { LectureDetail } from "@/lib/lesson/types";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string; lectureSlug: string }> }
) {
  try {
    const { slug, lectureSlug } = await params;

    const { status, data } = await ApiProxy.get<LectureDetail>(
      `/lesson/${slug}/lectures/${lectureSlug}/`,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch lecture:", error);

    return NextResponse.json(
      { message: "Failed to fetch lecture" },
      { status: 500 }
    );
  }
}