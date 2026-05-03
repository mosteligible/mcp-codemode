"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  MessageCirclePlus,
  Moon,
  MoreVertical,
  Pencil,
  SendHorizontal,
  Server,
  Sun,
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

type Theme = "light" | "dark";

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
  const [isThreadMenuOpen, setIsThreadMenuOpen] = useState(false);
  const [isRenameOpen, setIsRenameOpen] = useState(false);
  const [renameTitle, setRenameTitle] = useState("");
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  const [theme, setTheme] = useState<Theme>("light");

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

  function openRenameModal() {
    setRenameTitle(activeThread?.title ?? "New thread");
    setIsThreadMenuOpen(false);
    setIsRenameOpen(true);
  }

  async function saveThreadTitle(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!activeThreadId || isSavingTitle) return;

    const nextTitle = renameTitle.trim();
    if (!nextTitle) return;

    setIsSavingTitle(true);
    setError(null);

    try {
      const response = await fetch(`/api/threads/${activeThreadId}`, {
        method: "PATCH",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({ title: nextTitle }),
      });

      if (!response.ok) {
        throw new Error(await readError(response));
      }

      const payload = (await response.json()) as { thread: ThreadRecord };
      await refreshThreads();
      setActiveThreadId(payload.thread.id);
      setMessages(payload.thread.messages);
      setIsRenameOpen(false);
    } catch (renameError) {
      setError(renameError instanceof Error ? renameError.message : "Could not rename thread");
    } finally {
      setIsSavingTitle(false);
    }
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

  useEffect(() => {
    setIsThreadMenuOpen(false);
    setIsRenameOpen(false);
  }, [activeThreadId]);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("codemode-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const nextTheme = savedTheme === "dark" || savedTheme === "light"
      ? savedTheme
      : prefersDark
        ? "dark"
        : "light";

    setTheme(nextTheme);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("codemode-theme", theme);
  }, [theme]);

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

  function handleComposerKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    if (event.shiftKey) return;

    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  function toggleTheme() {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }

  return (
    <>
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
            <div className="thread-title-row">
              <div className="thread-menu-wrap">
                <button
                  className="title-menu-button"
                  type="button"
                  aria-label="Thread actions"
                  aria-expanded={isThreadMenuOpen}
                  onClick={() => setIsThreadMenuOpen((value) => !value)}
                  disabled={!activeThreadId}
                >
                  <MoreVertical size={16} />
                </button>
                {isThreadMenuOpen ? (
                  <div className="thread-menu">
                    <button type="button" onClick={openRenameModal}>
                      <Pencil size={14} />
                      <span>Edit</span>
                    </button>
                  </div>
                ) : null}
              </div>
              <h2>{activeThread?.title ?? "New thread"}</h2>
            </div>
          </div>
          <div className="chat-header-actions">
            <button
              className="theme-toggle"
              type="button"
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-pressed={theme === "dark"}
              onClick={toggleTheme}
              title={theme === "dark" ? "Light mode" : "Dark mode"}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <div className="activity-pill">
              <Activity size={14} />
              <span>{isStreaming ? "Streaming" : "Idle"}</span>
            </div>
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
            onKeyDown={handleComposerKeyDown}
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

      {isRenameOpen ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isSavingTitle) {
              setIsRenameOpen(false);
            }
          }}
        >
          <form
            className="rename-modal"
            onSubmit={saveThreadTitle}
            role="dialog"
            aria-modal="true"
            aria-labelledby="rename-thread-title"
          >
            <h3 id="rename-thread-title">Edit thread name</h3>
            <label className="rename-field">
              <span>Name</span>
              <input
                value={renameTitle}
                onChange={(event) => setRenameTitle(event.target.value)}
                maxLength={120}
                autoFocus
              />
            </label>
            <div className="modal-actions">
              <button
                className="secondary-action"
                type="button"
                onClick={() => setIsRenameOpen(false)}
                disabled={isSavingTitle}
              >
                Cancel
              </button>
              <button
                className="primary-action"
                type="submit"
                disabled={isSavingTitle || !renameTitle.trim()}
              >
                {isSavingTitle ? "Saving" : "Save"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </>
  );
}
