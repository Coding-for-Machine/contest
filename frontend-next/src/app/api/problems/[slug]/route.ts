import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { ProblemDetail } from "@/lib/problems/types";

interface RouteParams {
  params: Promise<{ slug: string }>;
}

export async function GET(_request: Request, { params }: RouteParams) {
  try {
    const { slug } = await params;

    // withAuth: true — "solved" statusi joriy foydalanuvchi uchun hisoblanishi
    // kerak (backend get_current_user_option orqali Authorization'ga qaraydi)
    const { status, data } = await ApiProxy.get<ProblemDetail>(`/problems/${slug}/`, {
      withAuth: true,
      cache: "no-store",
    });

    if (status >= 400) {
      return NextResponse.json(
        data || { detail: "Masala topilmadi" },
        { status }
      );
    }

    return NextResponse.json(data, { status });
  } catch (error: any) {
    console.error("Problem detail proxy xatolik:", error);
    return NextResponse.json(
      { detail: "Ichki proxy xatoligi yuz berdi" },
      { status: 500 }
    );
  }
}