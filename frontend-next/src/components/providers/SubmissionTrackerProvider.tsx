"use client";

import { useSSEEvent } from "@/hooks/useSSEEvent";
import submissionTracker from "@/lib/submissions/tracker";
import type {
  TestcasePayload,
  FinalPayload,
  ErrorPayload,
} from "@/lib/sse/types";

const onTestcase = (d: TestcasePayload) => submissionTracker.testcase(d);
const onFinal = (d: FinalPayload) => submissionTracker.final(d);
const onError = (d: ErrorPayload) => submissionTracker.error(d);

export function SubmissionTrackerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useSSEEvent("testcase", onTestcase);
  useSSEEvent("final", onFinal);
  useSSEEvent("error", onError);

  return <>{children}</>;
}