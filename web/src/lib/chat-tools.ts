import { tool, type ToolSet } from "ai";
import { z } from "zod";

import { callMcpTool, listMcpTools } from "./mcp";

function sanitizeToolName(name: string): string {
  return name
    .replace(/[^a-zA-Z0-9_]/g, "_")
    .replace(/_{2,}/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 50);
}

export async function buildMcpToolSet(input: {
  mcpServerUrls: string[];
  listTimeoutMs: number;
  callTimeoutMs: number;
}): Promise<ToolSet> {
  const tools = await listMcpTools(input.mcpServerUrls, input.listTimeoutMs);

  const entries = tools.map((item) => {
    const toolName = `mcp_${item.serverId}_${sanitizeToolName(item.name)}`;

    return [
      toolName,
      tool({
        description:
          `${item.description}\n` +
          `Server: ${item.serverUrl}\n` +
          `Original tool: ${item.name}`,
        inputSchema: z.object({
          arguments: z.record(z.string(), z.any()).default({}),
        }),
        execute: async ({ arguments: args }) => {
          return callMcpTool(item.serverUrl, item.name, args, input.callTimeoutMs);
        },
      }),
    ] as const;
  });

  return Object.fromEntries(entries);
}
