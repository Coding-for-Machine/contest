// app/(auth)/login/page.tsx
"use client";

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type KeyboardEvent,
  type ClipboardEvent,
  type FormEvent,
} from "react";
import { Loader2, Send } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useSearchParams, useRouter } from "next/navigation";
import Image from "next/image";

const OTP_LENGTH = 6;
const BOT_USERNAME = "cfm_login_bot";

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [digits, setDigits] = useState<string[]>(Array(OTP_LENGTH).fill(""));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [shake, setShake] = useState(false);
  const [mounted, setMounted] = useState(false);

  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  const otp = digits.join("");
  const isComplete = otp.length === OTP_LENGTH && digits.every((d) => d !== "");

  // Agar allaqachon login qilgan bo'lsa, qayta yo'naltirish
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      const next = searchParams.get("next");
      const invalidNext = ["/login", "/logout"];
      const redirectTo =
        next && next.startsWith("/") && !invalidNext.includes(next)
          ? next
          : "/";
      router.replace(redirectTo);
    }
  }, [isLoading, isAuthenticated, searchParams, router]);

  // Mount animatsiyasi
  useEffect(() => {
    setMounted(true);
    const t = setTimeout(() => inputsRef.current[0]?.focus(), 100);
    return () => clearTimeout(t);
  }, []);

  const setDigitAt = useCallback((index: number, value: string) => {
    setDigits((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }, []);

  const focusInput = useCallback((index: number) => {
    const el = inputsRef.current[index];
    if (el) {
      el.focus();
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, []);

  const triggerError = useCallback((message: string) => {
    setError(message);
    setShake(true);
    setDigits(Array(OTP_LENGTH).fill(""));
    setTimeout(() => {
      inputsRef.current[0]?.focus();
      setShake(false);
    }, 420);
  }, []);

  const handleChange = useCallback(
    (index: number, raw: string) => {
      const val = raw.replace(/\D/g, "").slice(-1);
      if (!val) return;
      setDigitAt(index, val);
      setError("");
      if (index < OTP_LENGTH - 1) focusInput(index + 1);
    },
    [focusInput, setDigitAt]
  );

  const handleKeyDown = useCallback(
    (index: number, e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Backspace") {
        e.preventDefault();
        if (digits[index]) {
          setDigitAt(index, "");
        } else if (index > 0) {
          setDigitAt(index - 1, "");
          focusInput(index - 1);
        }
      }
      if (e.key === "ArrowLeft" && index > 0) focusInput(index - 1);
      if (e.key === "ArrowRight" && index < OTP_LENGTH - 1)
        focusInput(index + 1);
      if (/^\d$/.test(e.key) && digits[index] && index < OTP_LENGTH - 1) {
        focusInput(index + 1);
      }
    },
    [digits, focusInput, setDigitAt]
  );

  const handlePaste = useCallback(
    (e: ClipboardEvent) => {
      e.preventDefault();
      const text = e.clipboardData
        .getData("text")
        .replace(/\D/g, "")
        .slice(0, OTP_LENGTH);
      if (!text) return;
      const next = Array(OTP_LENGTH).fill("");
      text.split("").forEach((c, i) => (next[i] = c));
      setDigits(next);
      setError("");
      setTimeout(() => {
        const idx = Math.min(text.length, OTP_LENGTH - 1);
        inputsRef.current[idx]?.focus();
      }, 10);
    },
    []
  );

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!isComplete || loading) return;
      setLoading(true);
      setError("");

      try {
        const res = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ otp }),
        });
        const data = await res.json();
        if (!res.ok) {
          triggerError(data.error ?? "Kod noto'g'ri yoki muddati o'tgan");
          return;
        }
        login(data.user);
      } catch {
        triggerError("Serverga ulanib bo'lmadi. Qayta urinib ko'ring.");
      } finally {
        setLoading(false);
      }
    },
    [isComplete, loading, otp, login, triggerError]
  );

  if (isLoading || isAuthenticated) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center overflow-hidden bg-white">
      <div
        className={`flex w-full max-w-sm flex-col items-center px-6 transition-all duration-500 ${
          mounted ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
        }`}
      >
        {/* Logo — dumaloq */}
        <div className="mb-2">
           <div className="relative h-16 w-16 overflow-hidden rounded-full ring-2 ring-gray-100">
              <Image
                src="/cfm_logo.webp"
                alt="CfM Contest"
                fill
                sizes="64px"
                className="object-cover"
                priority
              />
            </div>
        </div>

        <h1 className="mb-3 text-3xl font-bold tracking-tight text-gray-900">
          Kodni kiriting
        </h1>

        <p className="mb-8 max-w-xs text-center text-[15px] leading-relaxed text-gray-500">
          <a
            href={`https://t.me/${BOT_USERNAME}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-medium text-gray-900 underline decoration-gray-300 underline-offset-4 transition-colors hover:decoration-gray-500"
          >
            <Send className="h-3.5 w-3.5" strokeWidth={2.5} />
            @{BOT_USERNAME}
          </a>{" "}
          telegram botiga kiring va 1 daqiqalik kodingizni oling.
        </p>

        {/* OTP */}
        <form
          onSubmit={handleSubmit}
          className="flex w-full flex-col items-center gap-5"
        >
          <div
            className={`flex w-full justify-center gap-3 ${shake ? "animate-shake" : ""}`}
            onPaste={handlePaste}
            role="group"
            aria-label="Tasdiqlash kodi"
          >
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => {
                  inputsRef.current[i] = el;
                }}
                type="text"
                inputMode="numeric"
                autoComplete={i === 0 ? "one-time-code" : "off"}
                maxLength={1}
                value={digit}
                disabled={loading}
                aria-label={`${i + 1}-raqam`}
                aria-invalid={!!error}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                className={`h-14 w-12 rounded-xl border bg-white text-center text-xl font-semibold text-gray-900 outline-none transition-all
                  ${digit ? "border-orange-300" : "border-gray-200"}
                  focus:border-orange-400 focus:ring-[3px] focus:ring-orange-100
                  disabled:opacity-50`}
              />
            ))}
          </div>

          {error && (
            <p
              role="alert"
              className="-mt-1 w-full text-center text-sm font-medium text-red-500"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!isComplete || loading}
            className={`flex w-full items-center justify-center gap-2 rounded-xl py-3 text-[15px] font-semibold transition-all
              ${
                !isComplete || loading
                  ? "cursor-not-allowed bg-gray-100 text-gray-400"
                  : "bg-gray-900 text-white hover:bg-gray-800 active:scale-[0.98]"
              }`}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />
                Tekshirilmoqda...
              </>
            ) : (
              "Tasdiqlash"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-400">
          Kod kelmadimi? Botga qayta{" "}
          <span className="font-medium text-gray-600">/start</span> yozing.
        </p>
      </div>

      <style jsx global>{`
        html, body {
          overflow: hidden;
          height: 100%;
        }
        @keyframes shake {
          10%, 90% { transform: translateX(-1px); }
          20%, 80% { transform: translateX(2px); }
          30%, 50%, 70% { transform: translateX(-4px); }
          40%, 60% { transform: translateX(4px); }
        }
        .animate-shake {
          animation: shake 0.42s ease-in-out;
        }
      `}</style>
    </div>
  );
}