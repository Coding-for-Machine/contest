// app/api/proxy.ts
import { cookies } from "next/headers";
import { DJANGO_API_ENDPOINT } from "@/config/defaults";

type ProxyResponse<T = any> = { status: number; data: T };
type RequestBody = Record<string, any> | FormData | null;

type FetchOptions = {
  cache?: RequestCache;
  next?: { revalidate?: number; tags?: string[] };
  withAuth?: boolean; // 👈 Faqat token kerak bo'lsa true beriladi. Default: false
};

class ApiProxy {
  private static async getToken(): Promise<string | undefined> {
    const store = await cookies();
    return store.get("access_token")?.value;
  }

  // 👈 withAuth parametrini qabul qiladigan qildik
  private static async headers(isFormData = false, withAuth = false): Promise<HeadersInit> {
    const h: HeadersInit = {};
    if (!isFormData) h["Content-Type"] = "application/json";

    // 👈 Agar maxsus auth talab qilinsa va token bo'lsagina cookie o'qiladi
    if (withAuth) {
      const token = await this.getToken();
      if (token) h["Authorization"] = `Bearer ${token}`;
    }
    return h;
  }

  static async get<T = any>(
    endpoint: string,
    options: FetchOptions = {}
  ): Promise<ProxyResponse<T>> {
    const res = await fetch(`${DJANGO_API_ENDPOINT}${endpoint}`, {
      method: "GET",
      headers: await this.headers(false, options.withAuth), // 👈 options.withAuth uzatildi
      cache: options.cache ?? "no-store",
      next: options.next,
    });
    return this.handle<T>(res);
  }

  static async post<T = any>(endpoint: string, body: RequestBody, options: FetchOptions = {}) {
    const isForm = body instanceof FormData;
    const res = await fetch(`${DJANGO_API_ENDPOINT}${endpoint}`, {
      method: "POST",
      headers: await this.headers(isForm, options.withAuth), // 👈 options.withAuth uzatildi
      body: isForm ? body : JSON.stringify(body),
    });
    return this.handle<T>(res);
  }

  static async put<T = any>(endpoint: string, body: RequestBody, options: FetchOptions = {}) {
    const res = await fetch(`${DJANGO_API_ENDPOINT}${endpoint}`, {
      method: "PUT",
      headers: await this.headers(false, options.withAuth),
      body: JSON.stringify(body),
    });
    return this.handle<T>(res);
  }

  static async patch<T = any>(endpoint: string, body: RequestBody, options: FetchOptions = {}) {
    const res = await fetch(`${DJANGO_API_ENDPOINT}${endpoint}`, {
      method: "PATCH",
      headers: await this.headers(false, options.withAuth),
      body: JSON.stringify(body),
    });
    return this.handle<T>(res);
  }

  static async delete<T = any>(endpoint: string, options: FetchOptions = {}) {
    const res = await fetch(`${DJANGO_API_ENDPOINT}${endpoint}`, {
      method: "DELETE",
      headers: await this.headers(false, options.withAuth),
    });
    return this.handle<T>(res);
  }

  private static async handle<T>(res: Response): Promise<ProxyResponse<T>> {
    let data = null;
    try {
      data = await res.json();
    } catch {}
    return { status: res.status, data };
  }
}

export default ApiProxy;
