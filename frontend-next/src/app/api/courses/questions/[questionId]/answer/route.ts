import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import type {
  QuestionAnswerIn,
  QuestionAnswerResponse,
} from "@/lib/types/courses";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ questionId: string }> }
) {
  try {
    const { questionId } = await params;
    const body: QuestionAnswerIn = await req.json();

    const { status, data } = await ApiProxy.post<QuestionAnswerResponse>(
      `/questions/${questionId}/answer/`,
      body,
      { withAuth: true }
    );

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to submit question answer:", error);

    return NextResponse.json(
      { message: "Failed to submit question answer" },
      { status: 500 }
    );
  }
}