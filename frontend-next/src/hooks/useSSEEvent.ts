"use client";

import { useEffect } from "react";
import sseManager from "@/lib/sse/manager";
import { SSEEventMap, SSEListener } from "@/lib/sse/types";

export function useSSEEvent<K extends keyof SSEEventMap & string>(
  eventName: K,
  handler: (payload: SSEEventMap[K]) => void
) {
  useEffect(() => {
    const wrapped: SSEListener<SSEEventMap[K]> = (payload) => handler(payload);
    return sseManager.on(eventName, wrapped);
  }, [eventName, handler]);
}