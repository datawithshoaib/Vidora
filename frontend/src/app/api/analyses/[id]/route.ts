import { proxy } from "@/lib/proxy";

export async function GET(_request: Request, ctx: RouteContext<"/api/analyses/[id]">) {
  const { id } = await ctx.params;
  return proxy(`/analyses/${encodeURIComponent(id)}`);
}
