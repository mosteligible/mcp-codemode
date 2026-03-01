# mcp-codemode

This workspace has two main runtime components:

- `pyrunner`: MCP server with many tools and sandboxed code execution capacity.
- `client`: FastAPI server that runs agentic flows using the MCP server.

## Start Components Directly

### 1) Start `pyrunner` (MCP server)

```bash
cd pyrunner
uv run uvicorn main:app
```

### 2) Start `redis`, can be a docker container or a local instance

```bash
docker pull redis
docker run -p 6379:6379 --name redis -d redis
```

### 2) Start `client` (FastAPI + agent)

```bash
cd client
uv run main.py
```

## Start Components via Makefile

From the project root:

- Start MCP server:

```bash
make run-pyrunner
```

- Start client server:

```bash
make run-client
```

## Notes

- Start `pyrunner` first so the client can connect to the MCP endpoint.
- If needed, configure the client MCP URL in `client/config.py`.
