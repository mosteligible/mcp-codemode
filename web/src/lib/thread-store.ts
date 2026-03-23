import { randomUUID } from "node:crypto";

import type { ChatMessage, ChatRole, ThreadRecord, ThreadSummary } from "./types";

const threads = new Map<string, ThreadRecord>();

function nowIso(): string {
  return new Date().toISOString();
}

function formatTitle(source: string): string {
  const squashed = source.trim().replace(/\s+/g, " ");
  if (!squashed) return "New thread";
  return squashed.length <= 56 ? squashed : `${squashed.slice(0, 53)}...`;
}

function message(role: ChatRole, content: string): ChatMessage {
  return {
    id: randomUUID(),
    role,
    content,
    createdAt: nowIso(),
  };
}

export function createThread(title?: string): ThreadRecord {
  const createdAt = nowIso();
  const id = randomUUID();
  const thread: ThreadRecord = {
    id,
    title: formatTitle(title ?? "New thread"),
    createdAt,
    updatedAt: createdAt,
    messageCount: 0,
    messages: [],
  };

  threads.set(id, thread);
  return thread;
}

export function listThreads(): ThreadSummary[] {
  return Array.from(threads.values())
    .map((thread) => ({
      id: thread.id,
      title: thread.title,
      createdAt: thread.createdAt,
      updatedAt: thread.updatedAt,
      messageCount: thread.messageCount,
    }))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function getThread(threadId: string): ThreadRecord | null {
  return threads.get(threadId) ?? null;
}

export function ensureThread(threadId?: string): ThreadRecord {
  if (!threadId) {
    return createThread();
  }

  const existing = getThread(threadId);
  if (existing) return existing;
  return createThread();
}

export function appendMessage(
  threadId: string,
  role: ChatRole,
  content: string,
): ThreadRecord {
  const thread = getThread(threadId);

  if (!thread) {
    throw new Error(`Thread ${threadId} not found`);
  }

  if (!thread.messages.length && role === "user") {
    thread.title = formatTitle(content);
  }

  thread.messages.push(message(role, content));
  thread.messageCount = thread.messages.length;
  thread.updatedAt = nowIso();

  return thread;
}
