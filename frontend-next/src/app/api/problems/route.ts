import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type { ProblemsResponse } from "@/lib/problems/types";

function safePage(raw: string | null): number {
  const parsed = parseInt(raw ?? "1", 10);
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  return parsed;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;

    const page = safePage(searchParams.get("page"));
    const search = searchParams.get("search") ?? "";
    const categoryId = searchParams.get("category_id") ?? "";
    const tagId = searchParams.get("tag_id") ?? "";

    const limit = 10; // backenddagi MAX_LIMIT=50 ichida — xavfsiz qattiq qiymat
    const offset = (page - 1) * limit;

    const djangoParams = new URLSearchParams();
    djangoParams.set("limit", limit.toString());
    djangoParams.set("offset", offset.toString());

    if (search) djangoParams.set("search", search);
    if (categoryId) djangoParams.set("category_id", categoryId);
    if (tagId) djangoParams.set("tag_id", tagId);

    const { status, data } = await ApiProxy.get<ProblemsResponse>(
      `/problems/?${djangoParams.toString()}`,
      { withAuth: true, cache: "no-store" }
    );

    return NextResponse.json(data, { status });
  } catch (error: any) {
    console.error("Problems API proxy xatolik:", error);
    return NextResponse.json(
      { detail: "Ichki proxy xatoligi yuz berdi" },
      { status: 500 }
    );
  }
}