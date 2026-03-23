import { NextResponse } from "next/server";

import { getServerEnv } from "@/lib/env";
import { listMcpTools } from "@/lib/mcp";

export const runtime = "nodejs";

export async function GET() {
  try {
    const env = getServerEnv();

    const checks = await Promise.all(
      env.mcpServerUrls.map(async (url) => {
        try {
          const tools = await listMcpTools([url], env.mcpListTimeoutMs);
          return {
            url,
            ok: true,
            toolCount: tools.length,
          };
        } catch (error) {
          return {
            url,
            ok: false,
            error: error instanceof Error ? error.message : "Unknown MCP error",
          };
        }
      }),
    );

    return NextResponse.json({
      ok: true,
      model: env.openAiModel,
      mcpServers: checks,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Server configuration error",
      },
      { status: 500 },
    );
  }
}
