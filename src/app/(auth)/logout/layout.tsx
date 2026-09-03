import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Chiqish | CfM Contest",
  description: "Tizimdan chiqish",
};

export default function LogoutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <main className="min-h-screen bg-white antialiased">{children}</main>;
}

