import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { CallToolResultSchema, type CallToolResult } from "@modelcontextprotocol/sdk/types.js";

export interface McpServerDefinition {
  id: string;
  url: string;
}

export interface McpToolDefinition {
  serverId: string;
  serverUrl: string;
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
}

async function withMcpClient<T>(
  serverUrl: string,
  timeoutMs: number,
  run: (client: Client) => Promise<T>,
): Promise<T> {
  const client = new Client({
    name: "codemode-web",
    version: "0.1.0",
  });
  const transport = new StreamableHTTPClientTransport(new URL(serverUrl));

  try {
    await client.connect(transport, { timeout: timeoutMs });
    return await run(client);
  } finally {
    await client.close().catch(() => undefined);
  }
}

function serverDefs(urls: string[]): McpServerDefinition[] {
  return urls.map((url, index) => ({
    id: `server${index + 1}`,
    url,
  }));
}

export async function listMcpTools(
  urls: string[],
  timeoutMs: number,
): Promise<McpToolDefinition[]> {
  const servers = serverDefs(urls);

  const byServer = await Promise.all(
    servers.map(async (server) => {
      return withMcpClient(server.url, timeoutMs, async (client) => {
        const tools: McpToolDefinition[] = [];
        let cursor: string | undefined;

        do {
          const listed = await client.listTools(cursor ? { cursor } : undefined, {
            timeout: timeoutMs,
          });

          tools.push(
            ...listed.tools.map((tool) => ({
              serverId: server.id,
              serverUrl: server.url,
              name: tool.name,
              description: tool.description ?? "",
              inputSchema: tool.inputSchema,
            })),
          );

          cursor = listed.nextCursor;
        } while (cursor);

        return tools;
      });
    }),
  );

  return byServer.flat();
}

function stringifyContent(content: CallToolResult["content"]): string {
  if (!Array.isArray(content) || !content.length) {
    return "";
  }

  return content
    .map((chunk) => {
      if (chunk.type === "text") {
        return chunk.text ?? "";
      }

      if (chunk.type === "resource") {
        if ("text" in chunk.resource) return chunk.resource.text;
        return JSON.stringify(chunk.resource);
      }

      return JSON.stringify(chunk);
    })
    .join("\n")
    .trim();
}

export async function callMcpTool(
  serverUrl: string,
  name: string,
  args: Record<string, unknown>,
  timeoutMs: number,
): Promise<string> {
  return withMcpClient(serverUrl, timeoutMs, async (client) => {
    const result = await client.callTool(
      {
        name,
        arguments: args,
      },
      CallToolResultSchema,
      {
        timeout: timeoutMs,
        resetTimeoutOnProgress: true,
      },
    );

    if ("toolResult" in result) {
      return JSON.stringify(result.toolResult, null, 2);
    }

    const text = stringifyContent(result.content);
    if (text) {
      return result.isError ? `Tool returned an error:\n${text}` : text;
    }

    return JSON.stringify(result, null, 2);
  });
}
