import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { FinishTestResponse } from "@/lib/types/courses";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;

    const { status, data } = await ApiProxy.post<FinishTestResponse>(
      `/test-session/${sessionId}/finish/`,
      null,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to finish test:", error);

    return NextResponse.json(
      { message: "Failed to finish test" },
      { status: 500 }
    );
  }
}