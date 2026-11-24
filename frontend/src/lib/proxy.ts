import { NextResponse } from "next/server";

const apiUrl = () => process.env.VIDORA_API_URL ?? "http://127.0.0.1:8000";

export async function proxy(path: string, init?: RequestInit) {
  try {
    const response = await fetch(`${apiUrl()}${path}`, { ...init, cache: "no-store" });
    if (response.status === 204) return new NextResponse(null, { status: 204 });
    const body = await response.json().catch(() => ({}));
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "Cannot reach the Vidora API. Start it with python run.py." },
      { status: 503 },
    );
  }
}
