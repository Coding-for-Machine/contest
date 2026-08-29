// src/app/api/test-session/[sessionId]/result/route.ts
import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params;

  const res = await ApiProxy.get(`/courses/test-session/${sessionId}/result/`, {
    withAuth: true,
    cache: "no-store",
  });

  return NextResponse.json(res.data, { status: res.status });
}