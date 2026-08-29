// app/(auth)/logout/page.tsx
import type { Metadata } from "next";
import LogoutButton from './../../../components/LogoutButton';
export const metadata: Metadata = {
  title: "Tizimdan chiqish",
  robots: {
    index: false,
    follow: false,
  },
};

// 2. Asosiy sahifa (Server Component)
export default function LogoutPage() {
  return (
    <main className="flex-1 flex items-center justify-center p-4 bg-gray-50">
      <div className="max-w-md w-full border bg-white p-8 rounded-xl shadow-sm text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Tizimdan chiqish</h1>
        <p className="text-gray-500 mb-6">
          Hisobingizdan chiqmoqchimisiz? Istalgan vaqtda qayta kirishingiz mumkin.
        </p>
        
        {/* Pastdagi client komponentni shu yerda chaqiramiz */}
        <LogoutButton />
      </div>
    </main>
  );
}