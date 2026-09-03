import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { MyCoursesResponse } from "@/lib/types/courses";

export async function GET() {
  try {
    const { status, data } = await ApiProxy.get<MyCoursesResponse>(
      "/users/me/courses/",
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch my courses:", error);

    return NextResponse.json(
      { message: "Failed to fetch my courses" },
      { status: 500 }
    );
  }
}