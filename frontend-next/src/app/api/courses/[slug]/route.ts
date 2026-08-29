import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { CourseDetail } from "@/lib/types/course";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;

  const { status, data } = await ApiProxy.get<CourseDetail>(`/courses/${slug}/`, {
    withAuth: true,
    cache: "no-store",
  });

  if (status === 404 || !data) {
    return NextResponse.json({ detail: "Kurs topilmadi" }, { status: 404 });
  }

  return NextResponse.json(data, { status });
}