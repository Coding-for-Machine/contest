import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import { TestSessionResult } from "@/lib/types/courses";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;

    const { status, data } = await ApiProxy.get<TestSessionResult>(
      `/test-session/${sessionId}/result/`,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch test session result:", error);

    return NextResponse.json(
      { message: "Failed to fetch test session result" },
      { status: 500 }
    );
  }
}