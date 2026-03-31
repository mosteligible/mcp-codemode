# Codemode Web UI

Next.js App Router interface for chatting with an LLM via server-side OpenAI calls and MCP tools.

## Features

- TypeScript + App Router
- Streaming assistant responses
- Runtime-only thread memory (stored in server process memory)
- Server-side MCP integration with remote Streamable HTTP servers
- OpenAI model calls isolated to server routes

## Prerequisites

- Node.js 20+
- pnpm 10+
- A running MCP server (for local development this repo provides `pyrunner`)
- OpenAI API key

## Configuration

Create a local env file:

```bash
cp .env.example .env.local
```

Variables:

- `OPENAI_API_KEY` required for chat requests
- `OPENAI_MODEL` defaults to `gpt-4o-mini`
- `MCP_SERVER_URLS` comma-separated list of MCP Streamable HTTP endpoints
- `MCP_LIST_TIMEOUT_MS` timeout for tool discovery calls
- `MCP_CALL_TIMEOUT_MS` timeout for tool execution calls

Example:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
MCP_SERVER_URLS=http://localhost:8000/mcp
```

## Run

```bash
pnpm install
pnpm dev
```

Open `http://localhost:3000`.

## API Routes

- `POST /api/chat` stream assistant text for one user message in a thread
- `GET /api/threads` list in-memory threads
- `POST /api/threads` create a new thread
- `GET /api/threads/[threadId]` fetch a thread with messages
- `GET /api/status` check OpenAI config + MCP server reachability

## Notes

- Threads are intentionally non-persistent in v1. They reset when the Next.js process restarts.
- MCP tools are discovered server-side from configured endpoints.
- The web app is pinned to pnpm via the `packageManager` field in `package.json`.
