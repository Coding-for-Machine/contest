// src/app/api/courses/modul/[modulId]/test/route.ts
import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ modulId: string }> }
) {
  const { modulId } = await params;

  const res = await ApiProxy.get(`/courses/modul/${modulId}/test/`, {
    withAuth: true,
    cache: "no-store",
  });

  return NextResponse.json(res.data, { status: res.status });
}