// app/api/user/[username]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { getUserProfile } from "@/lib/api/users.server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ username: string }> }
) {
  const { username } = await params;

  try {
    const data = await getUserProfile(username);
    if (!data) {
      return NextResponse.json({ detail: "Foydalanuvchi topilmadi" }, { status: 404 });
    }
    return NextResponse.json(data);
  } catch (err) {
    console.error("[GET /api/user/:username]", err);
    return NextResponse.json({ detail: "Server xatoligi" }, { status: 502 });
  }
}