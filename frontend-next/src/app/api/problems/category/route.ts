// app/api/problems/category/route.ts
import ApiProxy from "@/app/api/proxy";
import { NextRequest, NextResponse } from "next/server";
import { Category } from "@/lib/problems/types";

export async function GET(request: NextRequest) {
  try {
    const { status, data } = await ApiProxy.get<Category[]>("/problems/categories/", {
      next: { revalidate: 3600 } 
    });
    
    return NextResponse.json(data, { status });
  } catch (error: any) {
    console.error("Category API proxy xatolik:", error);
    return NextResponse.json(
      { detail: "Ichki proxy xatoligi yuz berdi" },
      { status: 500 }
    );
  }
}
