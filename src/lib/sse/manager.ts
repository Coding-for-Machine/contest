type SSECallback = (data: any) => void;

class SSEManager {
  private eventSource: EventSource | null = null;
  private listeners: Map<string, Set<SSECallback>> = new Map();

  connect(url: string) {
    if (typeof window === "undefined") return;
    if (this.eventSource) {
      this.disconnect();
    }

    try {
      this.eventSource = new EventSource(url);

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit("message", data);
        } catch {
          this.emit("message", event.data);
        }
      };

      this.eventSource.onerror = (err) => {
        this.emit("error", err);
      };
    } catch (e) {
      console.error("SSE connection error", e);
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  subscribe(event: string, callback: SSECallback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    if (this.eventSource && event !== "message" && event !== "error") {
      this.eventSource.addEventListener(event, ((e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          callback(data);
        } catch {
          callback(e.data);
        }
      }) as EventListener);
    }

    return () => {
      this.unsubscribe(event, callback);
    };
  }

  unsubscribe(event: string, callback: SSECallback) {
    const set = this.listeners.get(event);
    if (set) {
      set.delete(callback);
    }
  }

  emit(event: string, data: any) {
    const set = this.listeners.get(event);
    if (set) {
      set.forEach((cb) => cb(data));
    }
  }
}

const sseManager = new SSEManager();
export default sseManager;
