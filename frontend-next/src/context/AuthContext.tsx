"use client";
// context/AuthContext.tsx
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { AuthUser } from "@/lib/types";

type AuthContextType = {
  isAuthenticated: boolean;
  user: AuthUser | null;
  isLoading: boolean;
  login: (user: AuthUser) => void;
  logout: () => Promise<void>;
  loginRequiredRedirect: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

const LOGIN_REDIRECT_URL = "/";
const LOGIN_REQUIRED_URL = "/login";
const LOCAL_STORAGE_KEY = "is-logged-in";
const LOCAL_USER_KEY = "auth-user";

// DIQQAT: token haqiqiyligini server bilan qayta-qayta tekshirish endi
// shart emas — buni har bir himoyalangan sahifaga kirishda src/proxy.ts
// (middleware) allaqachon bajaradi. Bu yerda faqat localStorage'dagi
// "optimistik" holatni saqlaymiz — tezkor UI uchun. Agar token haqiqatan
// eskirgan bo'lsa, foydalanuvchi keyingi himoyalangan sahifaga
// o'tishda proxy tomonidan /login'ga qaytariladi.

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Initial load — localStorage'dan o'qish
  useEffect(() => {
    const storedAuthStatus = localStorage.getItem(LOCAL_STORAGE_KEY);
    const storedUser = localStorage.getItem(LOCAL_USER_KEY);

    if (storedAuthStatus === "1" && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
        setIsAuthenticated(true);
      } catch {
        localStorage.removeItem(LOCAL_USER_KEY);
        localStorage.setItem(LOCAL_STORAGE_KEY, "0");
      }
    }
    setIsLoading(false);
  }, []);

  const login = (userData: AuthUser) => {
  const safeUser: AuthUser = {
    ...userData,
    username:
      userData.username?.trim() ||
      String(userData.telegramId ?? userData.id),
  };

  setIsAuthenticated(true);
  setUser(safeUser);

  localStorage.setItem(LOCAL_STORAGE_KEY, "1");
  localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(safeUser));

  const nextUrl = searchParams.get("next");

  const invalidNextUrl = ["/login", "/logout"];

  const nextUrlValid =
    nextUrl &&
    nextUrl.startsWith("/") &&
    !invalidNextUrl.includes(nextUrl);

  const redirectTo = nextUrlValid
    ? nextUrl
    : `/user/${safeUser.username}`;

  // MUHIM:
  // Next.js client navigation emas, haqiqiy browser navigation.
  window.location.assign(redirectTo);
};

  const logout = async () => {
    try {
      await fetch("/api/logout", { method: "POST" });
    } catch (err) {
      console.error("Logout so'rovida xato:", err);
    }
    setIsAuthenticated(false);
    setUser(null);
    localStorage.setItem(LOCAL_STORAGE_KEY, "0");
    localStorage.removeItem(LOCAL_USER_KEY);
    router.replace(LOGIN_REQUIRED_URL);
  };

  const loginRequiredRedirect = () => {
    setIsAuthenticated(false);
    setUser(null);
    localStorage.setItem(LOCAL_STORAGE_KEY, "0");
    localStorage.removeItem(LOCAL_USER_KEY);
    const loginWithNextUrl =
      pathname === LOGIN_REQUIRED_URL
        ? LOGIN_REQUIRED_URL
        : `${LOGIN_REQUIRED_URL}?next=${pathname}`;
    router.replace(loginWithNextUrl);
  };

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, user, isLoading, login, logout, loginRequiredRedirect }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth faqat AuthProvider ichida ishlatilishi kerak");
  }
  return context;
}