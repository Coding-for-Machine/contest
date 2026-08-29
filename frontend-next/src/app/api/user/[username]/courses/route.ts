import { NextRequest, NextResponse } from "next/server";
import { getUserCourses } from "@/lib/api/users.server";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ username: string }> }
) {
  const { username } = await params;
  const onlyActive = req.nextUrl.searchParams.get("only_active") === "true";

  const data = await getUserCourses(username, onlyActive);

  if (!data) {
    return NextResponse.json({ detail: "Foydalanuvchi topilmadi" }, { status: 404 });
  }
  return NextResponse.json(data);
}