import { NextResponse } from "next/server";
import ApiProxy from "@/app/api/proxy";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;

  const { status, data } = await ApiProxy.post(`/courses/${slug}/enroll/`, null, {
    withAuth: true,
  });

  return NextResponse.json(data, { status });
}