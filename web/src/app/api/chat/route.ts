import { stepCountIs, streamText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { NextResponse } from "next/server";
import { z } from "zod";

import { getAuthUserId } from "@/lib/auth";
import { buildMcpToolSet } from "@/lib/chat-tools";
import { buildBoundedModelMessages } from "@/lib/conversation-history";
import { getServerEnv } from "@/lib/env";
import { appendMessage, ensureThread, getThread } from "@/lib/thread-store";

const requestSchema = z.object({
  threadId: z.string().uuid(),
  message: z.string().min(1),
});

export const runtime = "nodejs";

export async function POST(request: Request) {
  const userId = await getAuthUserId();
  if (!userId) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  let env;
  try {
    env = getServerEnv();
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Server environment is invalid.",
      },
      { status: 500 },
    );
  }

  let payload;
  try {
    payload = requestSchema.parse(await request.json());
  } catch {
    return NextResponse.json({ error: "Invalid request payload." }, { status: 400 });
  }

  const thread = ensureThread(userId, payload.threadId);
  appendMessage(userId, thread.id, "user", payload.message);

  const hydratedThread = getThread(userId, thread.id);
  if (!hydratedThread) {
    return NextResponse.json({ error: "Thread not found." }, { status: 404 });
  }

  const modelMessages = buildBoundedModelMessages(
    hydratedThread.messages,
    env.conversationMaxTokens,
  );

  const openai = createOpenAI({ apiKey: env.openAiApiKey });

  const toolSet = await buildMcpToolSet({
    mcpServerUrls: env.mcpServerUrls,
    listTimeoutMs: env.mcpListTimeoutMs,
    callTimeoutMs: env.mcpCallTimeoutMs,
  });

  const result = streamText({
    model: openai(env.openAiModel),
    system:
      "You are a helpful coding assistant. You can use MCP tools when they help. " +
      "Use tools when external execution or filesystem interaction is needed.",
    messages: modelMessages,
    tools: toolSet,
    stopWhen: stepCountIs(5),
    onFinish: ({ text }) => {
      if (text.trim()) {
        appendMessage(userId, thread.id, "assistant", text);
      }
    },
  });

  return result.toTextStreamResponse({
    headers: {
      "x-thread-id": thread.id,
    },
  });
}
