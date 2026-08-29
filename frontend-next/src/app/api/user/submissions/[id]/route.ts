import { NextRequest, NextResponse } from "next/server";
import { getSubmissionDetail } from "@/lib/api/users.server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const submissionId = Number(id);

  if (!Number.isInteger(submissionId)) {
    return NextResponse.json({ detail: "Noto'g'ri submission id" }, { status: 400 });
  }

  const data = await getSubmissionDetail(submissionId);

  if (!data) {
    return NextResponse.json({ detail: "Submission topilmadi" }, { status: 404 });
  }
  return NextResponse.json(data);
}