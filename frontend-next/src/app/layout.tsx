import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Suspense } from "react";
import { AuthProvider } from "@/context/AuthContext";
import { SSEProvider } from "@/context/SSEProvider";
import { SubmissionTrackerProvider } from "@/components/providers/SubmissionTrackerProvider";
import { ConditionalNavbar } from "@/components/ConditionalNavbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "CfM Contest",
    template: "%s | CfM Contest",
  },
  description:
    "CfM Contest siz uchun harakat qiladi. Kuchli jamoa va yuqori bilimga ega oʻqituvchilarimiz sizga eng sifatli taʼlimni taqdim etadi.",
  metadataBase: new URL("https://cfmcontest.uz"),
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    title: "CfM Contest",
    description: "Kuchli jamoa va yuqori bilimga ega oʻqituvchilar bilan maqsadlaringizga erishing.",
    url: "https://cfmcontest.uz",
    siteName: "CfM Contest",
    locale: "uz_UZ",
    type: "website",
    images: [
      {
        url: "/cfm_logo.webp",
        width: 1200,
        height: 630,
        alt: "CfM Contest Ta'lim Platformasi",
      },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="uz"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex flex-col min-h-screen bg-white text-black antialiased">
        <Suspense fallback={null}>
          <AuthProvider>
            <SSEProvider>
              <SubmissionTrackerProvider>
                <ConditionalNavbar />
                {children}
              </SubmissionTrackerProvider>
            </SSEProvider>
          </AuthProvider>
        </Suspense>
      </body>
    </html>
  );
}