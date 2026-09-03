import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";
import { EnrollPaymentRequired, EnrollResponse } from "@/lib/types/courses";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params;

    const { status, data } = await ApiProxy.post<
      EnrollResponse | EnrollPaymentRequired
    >(`/${slug}/enroll`, null, {
      withAuth: true,
    });

    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Failed to enroll:", error);

    return NextResponse.json(
      { message: "Failed to enroll in course" },
      { status: 500 }
    );
  }
}