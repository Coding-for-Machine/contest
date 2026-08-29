import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { DJANGO_API_ENDPOINT } from "@/config/defaults";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const token = (await cookies())
      .get("access_token")
      ?.value;


    const response = await fetch(
      `${DJANGO_API_ENDPOINT}/code/run`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : {}),
        },
        body: JSON.stringify(body),
      }
    );


    const data = await response.json();


    return NextResponse.json(data, {
      status: response.status,
    });


  } catch (error) {

    console.error("RUN ERROR:", error);

    return NextResponse.json(
      {
        message: "Server xatosi",
      },
      {
        status: 500,
      }
    );
  }
}