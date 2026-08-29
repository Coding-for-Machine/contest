// app/api/problems/[slug]/navigation/route.ts
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { DJANGO_API_ENDPOINT } from "@/config/defaults";

export async function GET(
  request: NextRequest, 
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params;
    const direction = request.nextUrl.searchParams.get("direction") || "next";

    const token = (await cookies())
      .get("access_token")
      ?.value;

    const response = await fetch(
      `${DJANGO_API_ENDPOINT}/problems/${slug}/navigation/?direction=${direction}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : {}),
        },
        cache: "no-store",
      }
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });

  } catch (error) {
    console.error("NAVIGATION ERROR:", error);

    return NextResponse.json(
      {
        message: "Server xatosi",
      },
      {
        status: 500,
      }
    );
  }
}
