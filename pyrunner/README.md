# mcp-codemode

MCP server that provides sandboxed code execution via Docker containers. Clients (Claude Desktop, Cursor, custom orchestrators) connect over Streamable HTTP and get access to tools for running code, reading/writing files, and listing directory contents — all inside isolated, network-disabled containers.

## Prerequisites

- **Python 3.12+**
- **Docker** (daemon running, current user has access to the Docker socket)
- **uv** (Python package manager) — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Quick Start

```bash
cd pyrunner

# Install dependencies
uv sync

# Run the MCP server
uv run uvicorn main:app
```

The server starts on `http://0.0.0.0:8000` with the MCP endpoint at `/mcp`.

### Run via Docker

```bash
cd pyrunner
docker build -t mcp-codemode .

# Must mount the Docker socket so the server can manage sandbox containers
docker run -p 8000:8000 -v /var/run/docker.sock:/var/run/docker.sock mcp-codemode
```

## Configuration

All settings are read from environment variables:

| Variable | Default | Description |
|---|---|---|
| `SANDBOX_IMAGE` | `python:3.12-slim` | Docker image for sandbox containers |
| `POOL_SIZE` | `2` | Number of pre-spawned sandbox containers |
| `EXEC_TIMEOUT` | `30` | Max seconds per code execution |
| `MAX_OUTPUT_SIZE` | `50000` | Truncation limit for stdout/stderr (chars) |
| `MCP_HOST` | `0.0.0.0` | Server bind address |
| `MCP_PORT` | `8000` | Server bind port |
| `CONTAINER_MEMORY_LIMIT` | `256m` | Memory limit per sandbox container |
| `CONTAINER_CPU_LIMIT` | `1.0` | CPU limit per sandbox (fraction of one core) |

## Available Tools

### `execute_code`

Execute code in an isolated Docker sandbox with access.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `code` | `string` | *(required)* | Source code to execute |
| `language` | `string` | `"python"` | Language: `python`, `bash`, `sh`, `node`, `javascript` |

Returns formatted output with stdout, stderr, and exit code.

### `sandbox_read_file`

Read a file from the sandbox's `/workspace` directory.

| Parameter | Type | Description |
|---|---|---|
| `path` | `string` | File path (relative to /workspace, or absolute within /workspace) |

### `sandbox_write_file`

Write content to a file in the sandbox's `/workspace` directory.

| Parameter | Type | Description |
|---|---|---|
| `path` | `string` | File path (relative to /workspace, or absolute within /workspace) |
| `content` | `string` | Text content to write |

### `sandbox_list_files`

List directory contents inside the sandbox.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `string` | `"/workspace"` | Directory path (must be within /workspace) |

## Client Configuration

### Claude Desktop

Add to your Claude Desktop config (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-codemode": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### MCP Inspector (for testing)

```bash
npx @modelcontextprotocol/inspector
# Connect to: http://localhost:8000/mcp
```

## Architecture

```
Client (Claude Desktop / Cursor / custom)
    │
    │  MCP protocol over Streamable HTTP
    ▼
┌─────────────────────────────┐
│  FastMCP Server (main.py)   │
│  - Lifespan manages pool    │
│  - Tools registered at init │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  SandboxPool (sandbox.py)   │
│  - asyncio.Queue of Docker  │
│    containers               │
│  - acquire / release        │
│  - exec_code, file I/O      │
└──────────┬──────────────────┘
           │  Docker SDK
           ▼
┌─────────────────────────────┐
│  Docker Containers          │
│  - python:3.12-slim         │
│  - network_mode=none        │
│  - mem_limit, cpu_quota     │
│  - /workspace volume        │
└─────────────────────────────┘
```
