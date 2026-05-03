import { z } from "zod";

const defaultMcpHost = "http://localhost:8000/mcp";

const envSchema = z.object({
  OPENAI_API_KEY: z.string().min(1, "OPENAI_API_KEY is required"),
  OPENAI_MODEL: z.string().default("gpt-4o-mini"),
  MCP_HOST: z.string().optional(),
  MCP_SERVER_URLS: z.string().optional(),
  MCP_LIST_TIMEOUT_MS: z.coerce.number().int().positive().default(6000),
  MCP_CALL_TIMEOUT_MS: z.coerce.number().int().positive().default(25000),
  CONVERSATION_MAX_TOKENS: z.coerce.number().int().positive().default(200000),
});

export type ServerEnv = {
  openAiApiKey: string;
  openAiModel: string;
  mcpServerUrls: string[];
  mcpListTimeoutMs: number;
  mcpCallTimeoutMs: number;
  conversationMaxTokens: number;
};

function normalizeUrls(value: string): string[] {
  return value
    .split(",")
    .map((url) => url.trim())
    .filter(Boolean);
}

function normalizeMcpHost(value: string): string {
  const trimmed = value.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `http://${trimmed}`;
}

export function getServerEnv(): ServerEnv {
  const parsed = envSchema.safeParse(process.env);

  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    throw new Error(`Invalid environment configuration: ${issue.path.join(".")} ${issue.message}`);
  }

  const rawMcpHosts =
    parsed.data.MCP_HOST?.trim() ||
    parsed.data.MCP_SERVER_URLS?.trim() ||
    defaultMcpHost;

  return {
    openAiApiKey: parsed.data.OPENAI_API_KEY,
    openAiModel: parsed.data.OPENAI_MODEL,
    mcpServerUrls: normalizeUrls(rawMcpHosts).map(normalizeMcpHost),
    mcpListTimeoutMs: parsed.data.MCP_LIST_TIMEOUT_MS,
    mcpCallTimeoutMs: parsed.data.MCP_CALL_TIMEOUT_MS,
    conversationMaxTokens: parsed.data.CONVERSATION_MAX_TOKENS,
  };
}
