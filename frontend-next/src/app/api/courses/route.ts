import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import { CourseListResponse } from "@/lib/types/courses";

export async function GET() {
  try {
    const { status, data } = await ApiProxy.get<CourseListResponse>("/", {
      withAuth: true,
    });

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch courses:", error);

    return NextResponse.json(
      { message: "Failed to fetch courses" },
      { status: 500 }
    );
  }
}