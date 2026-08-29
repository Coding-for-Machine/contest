// components/ConditionalNavbar.tsx
"use client";

import { usePathname } from "next/navigation";
import { Navbar } from "@/components/Navbar";

// Navbar yashirilishi kerak bo'lgan yo'llar (prefix bo'yicha)
const HIDDEN_PREFIXES = ["/problem/"];

export function ConditionalNavbar() {
  const pathname = usePathname();

  const shouldHide = HIDDEN_PREFIXES.some((prefix) => pathname?.startsWith(prefix));

  if (shouldHide) return null;

  return <Navbar />;
}