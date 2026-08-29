import { NextRequest, NextResponse } from "next/server";
import { getUserActivity } from "@/lib/api/users.server";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ username: string }> }
) {
  const { username } = await params;
  const limitParam = req.nextUrl.searchParams.get("limit");

  const data = await getUserActivity(username, limitParam ? Number(limitParam) : undefined);

  if (!data) {
    return NextResponse.json({ detail: "Foydalanuvchi topilmadi" }, { status: 404 });
  }
  return NextResponse.json(data);
}