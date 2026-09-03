import type { TestcasePayload, FinalPayload } from "@/lib/sse/types";
import type { SubmissionStreamStatus, ActiveSubmission } from "@/components/problems/submission-result-modal";

export type TrackedSubmission = ActiveSubmission;

type Listener = (submission: TrackedSubmission | null) => void;

class SubmissionTracker {
  private current: TrackedSubmission | null = null;
  private listeners: Set<Listener> = new Set();
  private eventSource: EventSource | null = null;

  get(): TrackedSubmission | null {
    return this.current;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.current);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify() {
    for (const listener of this.listeners) {
      listener(this.current);
    }
  }

  start(taskId: string | number) {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.current = {
      id: taskId,
      status: "running",
      testcases: [],
      final: null,
      errorMessage: null,
    };
    this.notify();

    // Try connecting to SSE endpoint if in browser
    if (typeof window !== "undefined") {
      try {
        const es = new EventSource(`/api/submissions/stream/${taskId}`);
        this.eventSource = es;

        es.addEventListener("testcase", (e: MessageEvent) => {
          try {
            const data: TestcasePayload = JSON.parse(e.data);
            if (this.current) {
              this.current = {
                ...this.current,
                testcases: [...this.current.testcases, data],
              };
              this.notify();
            }
          } catch {
            // ignore
          }
        });

        es.addEventListener("final", (e: MessageEvent) => {
          try {
            const data: FinalPayload = JSON.parse(e.data);
            if (this.current) {
              this.current = {
                ...this.current,
                status: "done",
                final: data,
              };
              this.notify();
            }
            es.close();
            this.eventSource = null;
          } catch {
            // ignore
          }
        });

        es.onerror = () => {
          es.close();
          this.eventSource = null;
          // Fallback simulation for preview if SSE is not running backend
          this.simulateFallback(taskId);
        };
      } catch {
        this.simulateFallback(taskId);
      }
    }
  }

  private simulateFallback(taskId: string | number) {
    if (!this.current || this.current.status === "done") return;

    setTimeout(() => {
      if (!this.current) return;
      const tc1: TestcasePayload = {
        index: 1,
        status: "AC",
        cpu_time: 25,
        memory: 14.5 * 1024 * 1024,
      };
      this.current = {
        ...this.current,
        testcases: [tc1],
      };
      this.notify();

      setTimeout(() => {
        if (!this.current) return;
        const tc2: TestcasePayload = {
          index: 2,
          status: "AC",
          cpu_time: 32,
          memory: 14.8 * 1024 * 1024,
        };
        this.current = {
          ...this.current,
          status: "done",
          testcases: [tc1, tc2],
          final: {
            verdict: "AC",
            passed_count: 2,
            total_count: 2,
            lang: "python",
            time: 0.032,
            memory: 14.8,
          },
        };
        this.notify();
      }, 800);
    }, 600);
  }

  clear() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.current = null;
    this.notify();
  }
}

const submissionTracker = new SubmissionTracker();
export default submissionTracker;
