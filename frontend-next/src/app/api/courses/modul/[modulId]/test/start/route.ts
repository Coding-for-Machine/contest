import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { StartTestSessionResponse } from "@/lib/types/courses";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ modulId: string }> }
) {
  try {
    const { modulId } = await params;

    const { status, data } = await ApiProxy.post<StartTestSessionResponse>(
      `/modul/${modulId}/test/start/`,
      null,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to start test session:", error);

    return NextResponse.json(
      { message: "Failed to start test session" },
      { status: 500 }
    );
  }
}