import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { TestAnswerIn, TestAnswerResponse } from "@/lib/types/courses";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;
    const body: TestAnswerIn = await req.json();

    const { status, data } = await ApiProxy.post<TestAnswerResponse>(
      `/test-session/${sessionId}/answer/`,
      body,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to submit test answer:", error);

    return NextResponse.json(
      { message: "Failed to submit test answer" },
      { status: 500 }
    );
  }
}