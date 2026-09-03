export interface TestcasePayload {
  index: number;
  status: string;
  cpu_time?: number | null;
  memory?: number | null;
  input?: string | null;
  expected_output?: string | null;
  output?: string | null;
  error_msg?: string | null;
}

export interface FinalPayload {
  verdict: string;
  passed_count: number;
  total_count: number;
  lang: string;
  time: number;
  memory: number;
}
