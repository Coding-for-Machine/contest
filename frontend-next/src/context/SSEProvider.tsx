"use client";

import { useEffect } from "react";
import sseManager from "@/lib/sse/manager";
import { useAuth } from "@/context/AuthContext";

export function SSEProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;

    console.log("SSE AUTH:", isAuthenticated);

    sseManager.setAuthenticated(isAuthenticated);

    return () => {
      sseManager.disconnect();
    };

  }, [isAuthenticated, isLoading]);


  return <>{children}</>;
}