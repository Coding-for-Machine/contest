"use client";

import { useEffect, useState } from "react";
import sseManager from "@/lib/sse/manager";
import { SSEStatus } from "@/lib/sse/types";

export function useConnectionState() {
  const [status, setStatus] = useState<SSEStatus>(
    sseManager.getStatus()
  );

  useEffect(() => {
    return sseManager.onStatus(setStatus);
  }, []);

  return status;
}