import { randomUUID } from "node:crypto";

import type { ChatMessage, ChatRole, ThreadRecord, ThreadSummary } from "./types";

type StoredThread = ThreadRecord & {
  ownerId: string;
};

const threads = new Map<string, StoredThread>();
const userTitledThreads = new Set<string>();

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

function publicThread(thread: StoredThread): ThreadRecord {
  return {
    id: thread.id,
    title: thread.title,
    createdAt: thread.createdAt,
    updatedAt: thread.updatedAt,
    messageCount: thread.messageCount,
    messages: thread.messages,
  };
}

export function createThread(ownerId: string, title?: string): ThreadRecord {
  const createdAt = nowIso();
  const id = randomUUID();
  const thread: StoredThread = {
    id,
    ownerId,
    title: formatTitle(title ?? "New thread"),
    createdAt,
    updatedAt: createdAt,
    messageCount: 0,
    messages: [],
  };

  threads.set(id, thread);
  if (title) {
    userTitledThreads.add(id);
  }

  return publicThread(thread);
}

export function listThreads(ownerId: string): ThreadSummary[] {
  return Array.from(threads.values())
    .filter((thread) => thread.ownerId === ownerId)
    .map((thread) => ({
      id: thread.id,
      title: thread.title,
      createdAt: thread.createdAt,
      updatedAt: thread.updatedAt,
      messageCount: thread.messageCount,
    }))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function getThread(ownerId: string, threadId: string): ThreadRecord | null {
  const thread = threads.get(threadId);
  if (!thread || thread.ownerId !== ownerId) return null;

  return publicThread(thread);
}

export function updateThreadTitle(
  ownerId: string,
  threadId: string,
  title: string,
): ThreadRecord | null {
  const thread = threads.get(threadId);
  if (!thread || thread.ownerId !== ownerId) return null;

  thread.title = formatTitle(title);
  thread.updatedAt = nowIso();
  userTitledThreads.add(threadId);

  return publicThread(thread);
}

export function ensureThread(ownerId: string, threadId?: string): ThreadRecord {
  if (!threadId) {
    return createThread(ownerId);
  }

  const existing = getThread(ownerId, threadId);
  if (existing) return existing;
  return createThread(ownerId);
}

export function appendMessage(
  ownerId: string,
  threadId: string,
  role: ChatRole,
  content: string,
): ThreadRecord {
  const thread = threads.get(threadId);

  if (!thread || thread.ownerId !== ownerId) {
    throw new Error(`Thread ${threadId} not found`);
  }

  if (!thread.messages.length && role === "user" && !userTitledThreads.has(threadId)) {
    thread.title = formatTitle(content);
  }

  thread.messages.push(message(role, content));
  thread.messageCount = thread.messages.length;
  thread.updatedAt = nowIso();

  return publicThread(thread);
}
