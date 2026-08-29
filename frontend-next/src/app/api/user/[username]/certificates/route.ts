import { NextRequest, NextResponse } from "next/server";
import { getUserCertificates } from "@/lib/api/users.server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ username: string }> }
) {
  const { username } = await params;
  const data = await getUserCertificates(username);

  if (!data) {
    return NextResponse.json({ detail: "Foydalanuvchi topilmadi" }, { status: 404 });
  }
  return NextResponse.json(data);
}