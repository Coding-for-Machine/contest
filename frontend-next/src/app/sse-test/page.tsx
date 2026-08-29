"use client";

import { useState } from "react";
import { useConnectionState } from "@/hooks/useConnectionState";
import { useSSEEvent } from "@/hooks/useSSEEvent";
import {
  ErrorPayload,
  FinalPayload,
  LeaderboardPayload,
  QueuedPayload,
  ResultPayload,
  TestcasePayload,
  ContestLeaderboardPayload,
} from "@/lib/sse/types";

export default function SSETestPage() {
  const status = useConnectionState();

  const [queued, setQueued] = useState<QueuedPayload[]>([]);
  const [testcases, setTestcases] = useState<TestcasePayload[]>([]);
  const [results, setResults] = useState<ResultPayload[]>([]);
  const [finals, setFinals] = useState<FinalPayload[]>([]);
  const [errors, setErrors] = useState<ErrorPayload[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardPayload | null>(null);
  const [contestLeaderboard, setContestLeaderboard] =
    useState<ContestLeaderboardPayload | null>(null);

  useSSEEvent("queued", (payload) => {
    setQueued((prev) => [payload, ...prev].slice(0, 20));
  });

  useSSEEvent("testcase", (payload) => {
    setTestcases((prev) => [payload, ...prev].slice(0, 20));
  });

  useSSEEvent("result", (payload) => {
    setResults((prev) => [payload, ...prev].slice(0, 20));
  });

  useSSEEvent("final", (payload) => {
    setFinals((prev) => [payload, ...prev].slice(0, 20));
  });

  useSSEEvent("error", (payload) => {
    setErrors((prev) => [payload, ...prev].slice(0, 20));
  });

  useSSEEvent("leaderboard", (payload) => {
    setLeaderboard(payload);
  });

  useSSEEvent("contest_leaderboard", (payload) => {
    setContestLeaderboard(payload);
  });

  return (
    <div style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>SSE Test Page</h1>
      <p>Status: <b>{status}</b></p>

      <section style={{ marginTop: 24 }}>
        <h2>Queued</h2>
        <pre>{JSON.stringify(queued, null, 2)}</pre>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Testcase</h2>
        <pre>{JSON.stringify(testcases, null, 2)}</pre>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Result</h2>
        <pre>{JSON.stringify(results, null, 2)}</pre>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Final</h2>
        <pre>{JSON.stringify(finals, null, 2)}</pre>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Error</h2>
        <pre>{JSON.stringify(errors, null, 2)}</pre>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Leaderboard</h2>
        <pre>{JSON.stringify(leaderboard, null, 2)}</pre>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Contest Leaderboard</h2>
        <pre>{JSON.stringify(contestLeaderboard, null, 2)}</pre>
      </section>
    </div>
  );
}