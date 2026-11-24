export type JobStatus = "queued" | "processing" | "completed" | "failed";

export type Job = {
  id: string;
  status: JobStatus;
  step: "downloading" | "transcribing" | "analyzing" | null;
  error: string | null;
  analysis_id: string | null;
};

export type Analysis = {
  id: string;
  title: string;
  summary: string;
  action_items: string;
  key_decisions: string;
  open_questions: string;
  transcript: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, cache: "no-store" });
  } catch {
    throw new Error("Cannot reach the Vidora API. Start it with python run.py.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "Something went wrong. Try again.");
  }
  return body as T;
}

export const submitJob = (url: string) =>
  request<Job>("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

export const getJob = (id: string) => request<Job>(`/api/jobs/${id}`);
export const getAnalysis = (id: string) => request<Analysis>(`/api/analyses/${id}`);
