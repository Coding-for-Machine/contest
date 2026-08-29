// app/api/tests/modules/route.ts
//
// GET /api/tests/modules -> Django: GET {DJANGO_API_ENDPOINT}/tests/modules/
// Auth talab qilinmaydi — bu faqat filtr ro'yxati (bob testlari mavjud modullar).

import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET() {
  const { status, data } = await ApiProxy.get("/tests/modules/", {
    withAuth: false,
    next: { revalidate: 300 },
  });
  return NextResponse.json(data, { status });
}
