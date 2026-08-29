import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { ProblemStats } from "@/lib/problems/types";

export async function GET() {
  try {
    // DIQQAT: avvalgi versiyada "/stats" edi — Django'da bunday endpoint
    // yo'q, to'g'risi "/problems/stats/" (router "/problems" prefiksi
    // ostida mount qilingan, view esa "@api.get('/stats/')")
    const { data, status } = await ApiProxy.get<ProblemStats>("/problems/stats/", {
      withAuth: true,
      cache: "no-store",
    });

    return NextResponse.json(data, { status });
  } catch (error: any) {
    console.error("Stats api error:", error);
    return NextResponse.json(
      { detail: "Statistika ma'lumotlarini olishda xatolik yuz berdi" },
      { status: 500 }
    );
  }
}