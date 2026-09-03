import { NextResponse } from "next/server";
import { contests } from "@/lib/contests/mock-data";

export async function GET() {
  return NextResponse.json({
    results: contests,
    count: contests.length,
  });
}
