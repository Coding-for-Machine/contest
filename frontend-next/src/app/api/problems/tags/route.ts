// app/api/problems/tags/route.ts
import ApiProxy from "@/app/api/proxy";
import { NextResponse } from "next/server";
import { Tag } from "@/lib/problems/types";

export async function GET() {
  try {
    // DIQQAT: Django route'i "/tags/" (oxirida slash bilan) — slash'siz
    // yuborilsa APPEND_SLASH redirect qo'shimcha round-trip yaratadi.
    const { status, data } = await ApiProxy.get<Tag[]>("/problems/tags/", {
      next: { revalidate: 3600 },
    });

    return NextResponse.json(data, { status });
  } catch (error: any) {
    console.error("Tags API proxy xatolik:", error);
    return NextResponse.json(
      { detail: "Ichki proxy xatoligi yuz berdi" },
      { status: 500 }
    );
  }
}