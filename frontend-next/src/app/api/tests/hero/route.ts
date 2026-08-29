import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  const { status, data } = await ApiProxy.get(`/tests/hero`);
  return NextResponse.json(data, { status });
}
