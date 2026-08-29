// app/api/notifications/[id]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { DJANGO_API_ENDPOINT } from "@/config/defaults";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;

    const token = (await cookies())
      .get("access_token")
      ?.value;

    const response = await fetch(
      `${DJANGO_API_ENDPOINT}/notifications/${id}/`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          ...(token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : {}),
        },
      }
    );

    const data = await response.json().catch(() => null);

    return NextResponse.json(data, {
      status: response.status,
    });

  } catch (error: any) {
    console.error("Notification DELETE [id] error:", error);
    return NextResponse.json(
      { detail: "Xatolik yuz berdi" },
      { status: 500 }
    );
  }
}
