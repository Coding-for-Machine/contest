// app/api/tests/[slug]/route.ts
//
// GET /api/tests/{slug} -> Django: GET {DJANGO_API_ENDPOINT}/tests/{slug}
// withAuth: true — login qilingan bo'lsa `user` va `buy` (sotib olingan/olinmagan)
// maydonlari to'ldiriladi.
//
// Eslatma: Next.js versiyasiga qarab `params` Promise bo'lishi mumkin (Next 15+)
// yoki oddiy obyekt (Next 14 va oldingi). Quyida Next 15 formatida yozildi.

import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const { status, data } = await ApiProxy.get(`/tests/${slug}`, {
    withAuth: true,
    cache: "no-store",
  });
  return NextResponse.json(data, { status });
}
