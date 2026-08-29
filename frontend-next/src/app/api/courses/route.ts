// src/app/api/courses/route.ts
import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { CourseListItem } from "@/lib/types/course";

export async function GET() {
  const { status, data } = await ApiProxy.get<CourseListItem[]>("/courses/", {
    withAuth: true,
    cache: "no-store",
  });

  if (!data) {
    return NextResponse.json([], { status: 200 });
  }

  return NextResponse.json(data, { status });
}