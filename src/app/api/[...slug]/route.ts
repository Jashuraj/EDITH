import { NextRequest } from "next/server";
import { dispatch } from "@/server/routes";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Params = { params: Promise<{ slug: string[] }> };

/**
 * Single entry point for the EDITH gateway API.
 *  /api/compat/<legacy>  -> legacy root endpoints (rewritten from /cmd, /state, /stream/screen, ...)
 *  /api/auth/*, /api/pair/claim, /api/host/* (agent channel) -> mounted as-is
 *  everything else       -> "api/<...>" (matches the original EDITH /api/* contract)
 */
async function handler(req: NextRequest, { params }: Params) {
  const { slug } = await params;
  const head = slug[0];
  if (head === "compat") return dispatch(req, slug);
  const isCode = (head === "pair" || head === "host") && slug[1] === "code";
  if ((head === "auth" || head === "pair" || head === "host") && !isCode) return dispatch(req, slug);
  return dispatch(req, ["api", ...slug]);
}

export { handler as GET, handler as POST, handler as DELETE, handler as OPTIONS };
