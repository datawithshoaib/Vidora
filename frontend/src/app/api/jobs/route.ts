import { proxy } from "@/lib/proxy";

export async function GET() {
  return proxy("/jobs");
}

export async function POST(request: Request) {
  return proxy("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
  });
}
