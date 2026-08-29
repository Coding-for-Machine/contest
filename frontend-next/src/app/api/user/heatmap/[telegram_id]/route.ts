import { NextRequest, NextResponse } from "next/server";
import { getUserHeatmap } from "@/lib/api/users.server";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ telegram_id: string }> }
) {
  const { telegram_id } = await params;
  const telegramId = Number(telegram_id);

  if (!Number.isInteger(telegramId)) {
    return NextResponse.json({ detail: "Noto'g'ri telegram_id" }, { status: 400 });
  }

  const daysParam = req.nextUrl.searchParams.get("days");
  const data = await getUserHeatmap(telegramId, daysParam ? Number(daysParam) : undefined);

  if (!data) {
    return NextResponse.json({ detail: "Foydalanuvchi topilmadi" }, { status: 404 });
  }
  return NextResponse.json(data);
}