// src/app/api/courses/[slug]/audience/route.ts
import { NextResponse } from "next/server";
import { getCourseAudience } from "@/lib/data/course-audiences";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const data = getCourseAudience(slug);

  if (!data) {
    return NextResponse.json(
      { detail: "Kurs maqsadli auditoriyasi topilmadi" },
      { status: 404 }
    );
  }

  return NextResponse.json(data);
}