// src/app/api/courses/modul/[modulId]/test/start/route.ts
import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ modulId: string }> }
) {
  const { modulId } = await params;

  const res = await ApiProxy.post(
    `/courses/modul/${modulId}/test/start/`,
    null,
    { withAuth: true }
  );

  return NextResponse.json(res.data, { status: res.status });
}