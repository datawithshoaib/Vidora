import { proxy } from "@/lib/proxy";

export async function GET(_request: Request, ctx: RouteContext<"/api/analyses/[id]/chat">) {
  const { id } = await ctx.params;
  return proxy(`/analyses/${encodeURIComponent(id)}/chat`);
}

export async function POST(request: Request, ctx: RouteContext<"/api/analyses/[id]/chat">) {
  const { id } = await ctx.params;
  return proxy(`/analyses/${encodeURIComponent(id)}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
  });
}
