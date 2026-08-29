import { NextResponse } from "next/server";

const AUTH_API_ENDPOINT = process.env.AUTH_API_ENDPOINT ?? "http://localhost:8080";

export async function POST(request: Request) {
  let body: { otp?: string };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "JSON formatda yuborilishi kerak" },
      { status: 400 }
    );
  }

  if (!body?.otp) {
    return NextResponse.json({ error: "'otp' maydoni majburiy" }, { status: 422 });
  }

  let authRes: Response;
  try {
    authRes = await fetch(`${AUTH_API_ENDPOINT}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ otp: body.otp }),
    });
  } catch (err) {
    console.error("Auth serverga ulanishda xato:", err);
    return NextResponse.json(
      { error: "Auth serverga ulanib bo'lmadi" },
      { status: 502 }
    );
  }

  let data: any;
  try {
    data = await authRes.json();
  } catch {
    data = null;
  }

  if (!authRes.ok || !data?.t) {
    return NextResponse.json(
      { error: data?.error ?? "Login muvaffaqiyatsiz" },
      { status: authRes.status || 400 }
    );
  }

  // "id" auth serverda aslida telegram_id — shuni aniq ajratamiz
  const telegramId = data.u.id;
  // username bo'sh bo'lsa, telegramId'ni fallback sifatida ishlatamiz
  const username = data.u.u && data.u.u.trim() !== "" ? data.u.u : String(telegramId);

  const response = NextResponse.json(
    {
      success: true,
      user: {
        id: data.u.id,
        telegramId,
        username,
        phone: data.u.p,
        fullName: data.u.f,
        lastLogin: data.u.l,
      },
    },
    { status: 200 }
  );

  response.cookies.set("access_token", data.t, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24*300,
  });

  return response;
}