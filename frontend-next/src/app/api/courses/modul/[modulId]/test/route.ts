import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { TestInfo } from "@/lib/types/courses";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ modulId: string }> }
) {
  try {
    const { modulId } = await params;

    const { status, data } = await ApiProxy.get<TestInfo>(
      `/modul/${modulId}/test/`,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch test info:", error);

    return NextResponse.json(
      { message: "Failed to fetch test info" },
      { status: 500 }
    );
  }
}