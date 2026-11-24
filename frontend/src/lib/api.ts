export type JobStatus = "queued" | "processing" | "completed" | "failed";

export type Job = {
  id: string;
  source_kind: "youtube" | "upload";
  status: JobStatus;
  step: "downloading" | "preparing" | "transcribing" | "analyzing" | null;
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

export const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;
const EXTENSIONS = [
  "mp3", "wav", "m4a", "aac", "ogg", "oga", "opus", "flac", "wma", "weba",
  "mp4", "m4v", "mov", "mkv", "avi", "webm", "mpeg", "mpg", "3gp",
];
export const ACCEPT = EXTENSIONS.map((e) => `.${e}`).join(",");

/** Quick client-side hint; the API remains the authority. */
export function checkUpload(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!EXTENSIONS.includes(ext)) return "Unsupported file type. Choose an audio or video file such as MP3, WAV, M4A, MP4, MOV or WebM.";
  if (file.size > MAX_UPLOAD_BYTES) return "File is too large. The maximum upload size is 500 MB.";
  return null;
}

// Uploads go straight to the API (CORS enabled) because a Next.js route handler
// would buffer and cap large request bodies.
const API_URL = process.env.NEXT_PUBLIC_VIDORA_API_URL ?? "http://127.0.0.1:8000";

export function uploadMedia(file: File, onProgress: (fraction: number) => void): Promise<Job> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/jobs/upload`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    xhr.onerror = () => reject(new Error("Cannot reach the Vidora API. Start it with python run.py."));
    xhr.onload = () => {
      const body = xhr.response ?? {};
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as Job);
      else reject(new Error(typeof body.detail === "string" ? body.detail : "Upload failed. Try again."));
    };
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export const getJob = (id: string) => request<Job>(`/api/jobs/${id}`);
export const getAnalysis = (id: string) => request<Analysis>(`/api/analyses/${id}`);
