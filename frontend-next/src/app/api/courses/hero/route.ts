import { NextResponse } from "next/server";

import ApiProxy from "@/app/api/proxy";
import { HeroCourse } from "@/lib/types/courses";

export async function GET() {
  try {
    const { status, data } = await ApiProxy.get<HeroCourse | null>("/hero/");

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch hero course:", error);

    return NextResponse.json(
      { message: "Failed to fetch hero course" },
      { status: 500 }
    );
  }
}