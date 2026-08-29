import { NextRequest, NextResponse } from "next/server";
import { getUserHistory } from "@/lib/api/users.server";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ telegram_id: string }> }
) {
  const { telegram_id } = await params;
  const sp = req.nextUrl.searchParams;

  const data = await getUserHistory(telegram_id, {
    cursor: sp.get("cursor"),
    limit: sp.get("limit") ? Number(sp.get("limit")) : undefined,
    verdict: sp.get("verdict"),
  });

  if (!data) {
    return NextResponse.json({ detail: "Foydalanuvchi topilmadi" }, { status: 404 });
  }
  return NextResponse.json(data);
}