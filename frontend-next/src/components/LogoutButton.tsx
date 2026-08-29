// components/LogoutButton.tsx
"use client";

import { useAuth } from "@/context/AuthContext";

export default function LogoutButton() {
  const { logout } = useAuth();
  
  return (
    <button 
      onClick={logout}
      className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-6 rounded-md transition"
    >
      Tizimdan chiqish
    </button>
  );
}
