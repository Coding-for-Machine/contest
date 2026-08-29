// frontend-next/app/api/sse/stream/route.ts
export const runtime = "edge";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const userId = url.searchParams.get("user_id");
  
  const cookieHeader = request.headers.get("cookie") || "";
  const tokenMatch = cookieHeader.match(/access_token=([^;]+)/);
  const token = tokenMatch ? tokenMatch[1] : null;

  if (!token) {
    return new Response("Unauthorized", { status: 401 });
  }

  const backendUrl = new URL(`${process.env.DJANGO_API_ENDPOINT}/sse/stream`);
  backendUrl.searchParams.set("token", token);
  if (userId) backendUrl.searchParams.set("user_id", userId);

  const response = await fetch(backendUrl.toString(), {
    headers: { Accept: "text/event-stream" },
  });

  if (!response.ok || !response.body) {
    return new Response("Backend error", { status: 502 });
  }

  return new Response(response.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}