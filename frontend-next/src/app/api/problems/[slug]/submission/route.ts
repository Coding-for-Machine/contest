import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { ProblemSubmissionsResponse } from "@/lib/problems/types";

interface RouteParams {
  params: Promise<{ slug: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { slug } = await params;
    const sp = request.nextUrl.searchParams;

    const query = new URLSearchParams();
    const limit = sp.get("limit");
    const offset = sp.get("offset");
    if (limit) query.set("limit", limit);
    if (offset) query.set("offset", offset);
    const qs = query.toString() ? `?${query.toString()}` : "";

    // withAuth: MAJBURIY — Django tomoni request_user bo'lmasa bo'sh
    // ro'yxat qaytaradi (get_submission_list_for_user), token yubormasak
    // foydalanuvchi hech qachon o'z tarixini ko'ra olmaydi
    const { status, data } = await ApiProxy.get<ProblemSubmissionsResponse>(
      `/problems/${slug}/submission${qs}`,
      { withAuth: true, cache: "no-store" }
    );

    if (status >= 400) {
      return NextResponse.json(data || { detail: "Masala topilmadi" }, { status });
    }

    return NextResponse.json(data, { status });
  } catch (error: any) {
    console.error("Problem submissions proxy xatolik:", error);
    return NextResponse.json(
      { detail: "Ichki proxy xatoligi yuz berdi" },
      { status: 500 }
    );
  }
}