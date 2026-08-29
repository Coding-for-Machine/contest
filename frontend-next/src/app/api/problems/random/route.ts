// app/api/problems/random/route.ts
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { DJANGO_API_ENDPOINT } from "@/config/defaults";

export async function GET(request: NextRequest) {
  try {
    const sp = request.nextUrl.searchParams;
    const qs = sp.toString() ? `?${sp.toString()}` : "";

    const token = (await cookies())
      .get("access_token")
      ?.value;

    const response = await fetch(
      `${DJANGO_API_ENDPOINT}/problems/random/${qs}`,
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
    console.error("RANDOM PROBLEM ERROR:", error);
    
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
