// app/api/problems/[slug]/hls/video/route.ts
import { NextRequest, NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params;

    const { status, data } = await ApiProxy.get(
      `/problems/${slug}/hls/video/`,
      { withAuth: true, cache: "no-store" }
    );

    return NextResponse.json(data, { status });
  } catch (error: any) {
    console.error(`[HLS Video] ${slug}:`, error);
    return NextResponse.json(
      { detail: "Videoni yuklashda xatolik yuz berdi" },
      { status: 500 }
    );
  }
}