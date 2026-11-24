import { proxy } from "@/lib/proxy";

export async function GET(_request: Request, ctx: RouteContext<"/api/jobs/[id]">) {
  const { id } = await ctx.params;
  return proxy(`/jobs/${encodeURIComponent(id)}`);
}

export async function DELETE(_request: Request, ctx: RouteContext<"/api/jobs/[id]">) {
  const { id } = await ctx.params;
  return proxy(`/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
}
