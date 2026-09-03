import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import { QuestionDetail } from "@/lib/types/courses";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ questionId: string }> }
) {
  try {
    const { questionId } = await params;

    const { status, data } = await ApiProxy.get<QuestionDetail>(
      `/questions/${questionId}/`,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to fetch question:", error);

    return NextResponse.json(
      { message: "Failed to fetch question" },
      { status: 500 }
    );
  }
}