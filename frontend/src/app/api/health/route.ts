import { NextResponse } from "next/server";

export async function GET() {
  const apiUrl = process.env.VIDORA_API_URL ?? "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    if (!response.ok) {
      return NextResponse.json({ status: "unavailable" }, { status: 503 });
    }
    return NextResponse.json({ status: "ok" });
  } catch {
    return NextResponse.json({ status: "unavailable" }, { status: 503 });
  }
}
