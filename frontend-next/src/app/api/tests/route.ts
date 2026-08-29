// app/api/tests/route.ts
//
// GET /api/tests?limit=&offset=&search=&is_free=&only_available=
// -> Django: GET {DJANGO_API_ENDPOINT}/tests/?...
//
// withAuth: true — user login qilgan bo'lsa, natijaga uning `user` statistikasi
// (att/status/score/xp) qo'shib beriladi (backend get_current_user_option orqali).

import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  const { status, data } = await ApiProxy.get(`/tests/${qs ? `?${qs}` : ""}`, {
    withAuth: true,
    cache: "no-store",
  });
  return NextResponse.json(data, { status });
}
