import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import { LessonDetail, LessonLocked } from "@/lib/types/courses";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params;

    const { status, data } = await ApiProxy.get<LessonDetail | LessonLocked>(
      `/lesson/${slug}/`,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch lesson:", error);

    return NextResponse.json(
      { message: "Failed to fetch lesson" },
      { status: 500 }
    );
  }
}