import { jsonSchema, tool, type JSONSchema7, type ToolSet } from "ai";

import { callMcpTool, listMcpTools } from "./mcp";

const emptyObjectSchema: JSONSchema7 = {
  type: "object",
  properties: {},
};

function sanitizeToolName(name: string): string {
  return name
    .replace(/[^a-zA-Z0-9_]/g, "_")
    .replace(/_{2,}/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 50) || "tool";
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
        inputSchema: jsonSchema<Record<string, unknown>>(
          (item.inputSchema ?? emptyObjectSchema) as JSONSchema7,
        ),
        execute: async (args) => {
          return callMcpTool(item.serverUrl, item.name, args, input.callTimeoutMs);
        },
      }),
    ] as const;
  });

  return Object.fromEntries(entries);
}
