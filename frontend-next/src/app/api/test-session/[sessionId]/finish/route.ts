// src/app/api/test-session/[sessionId]/finish/route.ts
import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params;

  const res = await ApiProxy.post(
    `/courses/test-session/${sessionId}/finish/`,
    null,
    { withAuth: true }
  );

  return NextResponse.json(res.data, { status: res.status });
}