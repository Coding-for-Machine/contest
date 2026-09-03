import type { ApiError } from "./types";

export async function apiPost<T = any>(url: string, body?: any): Promise<T> {
  const finalUrl = url.startsWith("/api")
    ? url
    : `/api${url.startsWith("/") ? "" : "/"}${url}`;

  let res: Response;
  try {
    res = await fetch(finalUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (netErr: any) {
    const err: ApiError = {
      status: 0,
      message: netErr?.message || "Tarmoq xatoligi",
    };
    throw err;
  }

  if (!res.ok) {
    let detail: any = null;
    try {
      detail = await res.json();
    } catch {
      // ignore
    }
    const err: ApiError = {
      status: res.status,
      message:
        (detail && (detail.detail || detail.message)) ||
        `Server xatoligi (${res.status})`,
      detail,
    };
    throw err;
  }

  return await res.json();
}
