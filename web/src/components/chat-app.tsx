"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  MessageCirclePlus,
  SendHorizontal,
  Server,
  User,
} from "lucide-react";

import type { ChatMessage, ThreadRecord, ThreadSummary } from "@/lib/types";

interface StatusPayload {
  ok: boolean;
  model?: string;
  error?: string;
  mcpServers?: Array<{
    url: string;
    ok: boolean;
    toolCount?: number;
    error?: string;
  }>;
}

function isoNow(): string {
  return new Date().toISOString();
}

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

async function readError(response: Response): Promise<string> {
  const payload = await response
    .json()
    .catch(() => ({ error: "Request failed" }));

  if (payload && typeof payload.error === "string") {
    return payload.error;
  }

  return "Request failed";
}

export function ChatApp() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isBooting, setIsBooting] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeThread = useMemo(
    () => threads.find((thread) => thread.id === activeThreadId) ?? null,
    [threads, activeThreadId],
  );

  async function refreshStatus() {
    const response = await fetch("/api/status", { cache: "no-store" });
    const payload = (await response.json()) as StatusPayload;
    setStatus(payload);
  }

  async function refreshThreads() {
    const response = await fetch("/api/threads", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(await readError(response));
    }

    const payload = (await response.json()) as { threads: ThreadSummary[] };
    setThreads(payload.threads);
    return payload.threads;
  }

  async function createThread() {
    const response = await fetch("/api/threads", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      throw new Error(await readError(response));
    }

    const payload = (await response.json()) as { thread: ThreadRecord };
    setActiveThreadId(payload.thread.id);
    setMessages(payload.thread.messages);

    return payload.thread.id;
  }

  async function loadThread(threadId: string) {
    const response = await fetch(`/api/threads/${threadId}`, { cache: "no-store" });

    if (!response.ok) {
      throw new Error(await readError(response));
    }

    const payload = (await response.json()) as { thread: ThreadRecord };
    setActiveThreadId(payload.thread.id);
    setMessages(payload.thread.messages);
  }

  useEffect(() => {
    const init = async () => {
      try {
        setIsBooting(true);
        await refreshStatus();
        const loaded = await refreshThreads();

        if (loaded.length) {
          await loadThread(loaded[0].id);
        } else {
          await createThread();
          await refreshThreads();
        }
      } catch (initError) {
        setError(initError instanceof Error ? initError.message : "Unable to initialize");
      } finally {
        setIsBooting(false);
      }
    };

    void init();
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!activeThreadId || isStreaming) return;

    const message = input.trim();
    if (!message) return;

    setError(null);
    setInput("");

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      createdAt: isoNow(),
    };

    const assistantId = crypto.randomUUID();

    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: isoNow(),
      },
    ]);

    setIsStreaming(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          threadId: activeThreadId,
          message,
        }),
      });

      if (!response.ok) {
        throw new Error(await readError(response));
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response stream available.");
      }

      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const next = await reader.read();
        done = next.done;

        if (!next.value) continue;

        const chunk = decoder.decode(next.value, { stream: !done });

        setMessages((prev) =>
          prev.map((item) => {
            if (item.id !== assistantId) return item;
            return {
              ...item,
              content: `${item.content}${chunk}`,
            };
          }),
        );
      }

      await Promise.all([refreshThreads(), loadThread(activeThreadId)]);
    } catch (streamError) {
      const messageText = streamError instanceof Error ? streamError.message : "Chat request failed";
      setError(messageText);
      setMessages((prev) =>
        prev.map((item) => {
          if (item.id !== assistantId) return item;
          return {
            ...item,
            content: `Error: ${messageText}`,
          };
        }),
      );
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="chat-shell">
      <aside className="thread-rail">
        <div className="rail-header">
          <div>
            <p className="eyebrow">Runtime Threads</p>
            <h1>Codemode Chat</h1>
          </div>
          <button
            className="icon-button"
            onClick={() => {
              void (async () => {
                try {
                  setError(null);
                  const threadId = await createThread();
                  await refreshThreads();
                  await loadThread(threadId);
                } catch (threadError) {
                  setError(
                    threadError instanceof Error
                      ? threadError.message
                      : "Could not create thread",
                  );
                }
              })();
            }}
            aria-label="Create thread"
            type="button"
          >
            <MessageCirclePlus size={18} />
          </button>
        </div>

        <div className="status-card">
          <div className="status-title">
            <Server size={14} />
            <span>Server Status</span>
          </div>
          {status ? (
            <>
              <p className="status-model">Model: {status.model ?? "Unknown"}</p>
              <ul className="status-list">
                {(status.mcpServers ?? []).map((server) => (
                  <li key={server.url}>
                    <span className={server.ok ? "dot ok" : "dot down"} />
                    <span className="truncate" title={server.url}>
                      {server.url}
                    </span>
                    <span className="count">
                      {server.ok ? `${server.toolCount ?? 0} tools` : "offline"}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="status-model">Checking…</p>
          )}
        </div>

        <div className="thread-list">
          {threads.map((thread) => (
            <button
              className={`thread-row ${thread.id === activeThreadId ? "active" : ""}`}
              key={thread.id}
              onClick={() => {
                void loadThread(thread.id).catch((loadError: unknown) => {
                  setError(loadError instanceof Error ? loadError.message : "Could not load thread");
                });
              }}
              type="button"
            >
              <span className="title">{thread.title}</span>
              <span className="meta">{shortDate(thread.updatedAt)}</span>
            </button>
          ))}
        </div>
      </aside>

      <main className="chat-panel">
        <header className="chat-header">
          <div>
            <p className="eyebrow">Active Thread</p>
            <h2>{activeThread?.title ?? "New thread"}</h2>
          </div>
          <div className="activity-pill">
            <Activity size={14} />
            <span>{isStreaming ? "Streaming" : "Idle"}</span>
          </div>
        </header>

        <section className="message-stream">
          {isBooting ? <p className="empty">Preparing chat workspace…</p> : null}
          {!isBooting && !messages.length ? (
            <p className="empty">
              Ask for code help, architecture guidance, or tool-backed execution.
            </p>
          ) : null}

          {messages.map((message) => (
            <article key={message.id} className={`bubble ${message.role}`}>
              <div className="bubble-icon">
                {message.role === "user" ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div className="bubble-body">
                <p className="bubble-role">{message.role === "user" ? "You" : "Assistant"}</p>
                <p>{message.content || (isStreaming ? "…" : "")}</p>
              </div>
            </article>
          ))}
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask anything. MCP tools are available to the assistant."
            rows={3}
            disabled={isStreaming || !activeThreadId}
          />
          <div className="composer-footer">
            <p>{error ? `Error: ${error}` : "Threads persist only while the app process is running."}</p>
            <button type="submit" disabled={isStreaming || !input.trim() || !activeThreadId}>
              <SendHorizontal size={16} />
              <span>{isStreaming ? "Sending" : "Send"}</span>
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
