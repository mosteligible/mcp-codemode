import { randomUUID } from "node:crypto";

export interface MpcServerDefinition {
  id: string;
  url: string;
}

export interface MpcToolDefinition {
  serverId: string;
  serverUrl: string;
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
}

interface JsonRpcResponse<T> {
  id?: string;
  jsonrpc?: "2.0";
  result?: T;
  error?: {
    code: number;
    message: string;
  };
}

interface ToolsListResult {
  tools: Array<{
    name: string;
    description?: string;
    inputSchema?: Record<string, unknown>;
  }>;
}

interface ToolCallResult {
  content?: Array<{ type?: string; text?: string }>;
  isError?: boolean;
  [key: string]: unknown;
}

function withTimeout(signal: AbortSignal | undefined, timeoutMs: number): AbortSignal {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  signal?.addEventListener("abort", () => controller.abort(), { once: true });
  controller.signal.addEventListener(
    "abort",
    () => {
      clearTimeout(timeout);
    },
    { once: true },
  );

  return controller.signal;
}

async function jsonRpcRequest<T>(
  serverUrl: string,
  method: string,
  params: Record<string, unknown>,
  timeoutMs: number,
): Promise<T> {
  const response = await fetch(serverUrl, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: randomUUID(),
      method,
      params,
    }),
    signal: withTimeout(undefined, timeoutMs),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`MCP request failed (${response.status}) for ${method} on ${serverUrl}`);
  }

  const payload = (await response.json()) as JsonRpcResponse<T>;

  if (payload.error) {
    throw new Error(`MCP error ${payload.error.code}: ${payload.error.message}`);
  }

  if (!payload.result) {
    throw new Error(`MCP request missing result for method ${method}`);
  }

  return payload.result;
}

function serverDefs(urls: string[]): MpcServerDefinition[] {
  return urls.map((url, index) => ({
    id: `server${index + 1}`,
    url,
  }));
}

export async function listMcpTools(
  urls: string[],
  timeoutMs: number,
): Promise<MpcToolDefinition[]> {
  const servers = serverDefs(urls);

  const byServer = await Promise.all(
    servers.map(async (server) => {
      const listed = await jsonRpcRequest<ToolsListResult>(
        server.url,
        "tools/list",
        {},
        timeoutMs,
      );

      return listed.tools.map((tool) => ({
        serverId: server.id,
        serverUrl: server.url,
        name: tool.name,
        description: tool.description ?? "",
        inputSchema: tool.inputSchema,
      }));
    }),
  );

  return byServer.flat();
}

function stringifyContent(content: ToolCallResult["content"]): string {
  if (!Array.isArray(content) || !content.length) {
    return "";
  }

  return content
    .map((chunk) => {
      if (chunk.type === "text") {
        return chunk.text ?? "";
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
  const result = await jsonRpcRequest<ToolCallResult>(
    serverUrl,
    "tools/call",
    {
      name,
      arguments: args,
    },
    timeoutMs,
  );

  const text = stringifyContent(result.content);
  if (text) return text;

  return JSON.stringify(result, null, 2);
}
