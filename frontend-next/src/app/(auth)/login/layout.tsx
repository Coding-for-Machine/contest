// app/(auth)/login/layout.tsx
import type { Metadata } from "next";
import { AuthProvider } from "@/context/AuthContext";

const SITE_URL = "https://cfmcontest.uz";
const LOGO_PATH = "./cfm_logo.webp";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Kirish | CfM Contest",
  description:
    "CfM Contest platformasidagi shaxsiy kabinetingizga Telegram orqali xavfsiz va tezkor kiring.",

  // Qidiruv robotlariga ushbu sahifani indekslamaslikni buyuramiz
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      follow: false,
    },
  },

  alternates: {
    canonical: "/login",
  },

  // Ijtimoiy tarmoqlarda ulashilganda (Telegram, Twitter, Facebook) chiqadigan preview
  openGraph: {
    title: "Kirish | CfM Contest",
    description: "Telegram orqali bir zumda tizimga kiring.",
    url: `${SITE_URL}/login`,
    siteName: "CfM Contest",
    images: [
      {
        url: LOGO_PATH,
        width: 512,
        height: 512,
        alt: "CfM Contest",
      },
    ],
    locale: "uz_UZ",
    type: "website",
  },

  twitter: {
    card: "summary",
    title: "Kirish | CfM Contest",
    description: "Telegram orqali bir zumda tizimga kiring.",
    images: [LOGO_PATH],
  },

  // Brauzer tab'idagi ikonka
  icons: {
    icon: LOGO_PATH,
    shortcut: LOGO_PATH,
    apple: LOGO_PATH,
  },
};

export const viewport = {
  themeColor: "#ffffff",
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <main className="min-h-screen bg-white antialiased">{children}</main>
    </AuthProvider>
  );
}