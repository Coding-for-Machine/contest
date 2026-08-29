// app/api/tests/[slug]/sessions/route.ts
//
// GET /api/tests/{slug}/sessions?limit=&offset=
// -> Django: GET {DJANGO_API_ENDPOINT}/tests/{slug}/sessions?...
// withAuth: true (MAJBURIY) — backend get_current_user talab qiladi.
// Token bo'lmasa Django 401 qaytaradi, biz shuni to'g'ridan-to'g'ri uzatamiz.

import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const qs = req.nextUrl.searchParams.toString();
  const { status, data } = await ApiProxy.get(
    `/tests/${slug}/sessions${qs ? `?${qs}` : ""}`,
    { withAuth: true, cache: "no-store" }
  );
  return NextResponse.json(data, { status });
}
