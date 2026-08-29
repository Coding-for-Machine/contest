// app/api/tests/stats/route.ts
//
// GET /api/tests/stats -> Django: GET {DJANGO_API_ENDPOINT}/tests/stats/
// withAuth: true — login qilmagan foydalanuvchi uchun ham ishlaydi
// (backend get_current_user_option orqali None qabul qiladi), lekin
// login qilingan bo'lsa attempted/passed/total_xp to'ldiriladi.

import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET() {
  const { status, data } = await ApiProxy.get("/test-session/stats/", {
    withAuth: true,
    cache: "no-store",
  });
  return NextResponse.json(data, { status });
}
