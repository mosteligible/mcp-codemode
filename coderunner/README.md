# Coderunner

Coderunner is the Go control-plane service in this repo. It accepts code-execution requests over HTTP, forwards them to remote worker agents over gRPC, and also exposes an MCP server with GitHub tools.

## What It Runs Today

The current `main.go` starts two servers in one process:

- HTTP API on `:8080`
- MCP server on `:8081`

At startup, Coderunner:

- initializes OpenTelemetry tracing
- loads configuration from environment variables and `.env`
- creates gRPC clients for each host in `REMOTE_HOSTS`
- connects to Redis for proxy token lookup
- registers MCP tools for GitHub

## HTTP API

### `POST /run`

Executes code by forwarding the request to a remote agent via `Agent.ExecuteCode`.

Request body:

```json
{
  "code": "print('hello')",
  "language": "python",
  "sessionId": "optional-session-id"
}
```

Response body:

```json
{
  "output": "hello\n",
  "error": ""
}
```

Notes:

- `code` is required and must be non-empty after trimming.
- `language` is forwarded as-is to the worker.
- `sessionId` is optional.

### `GET /status`

Checks whether one connected worker responds to the gRPC `Status` RPC.

Successful response:

```json
{
  "status": 200
}
```

### `GET /proxy/{path...}` and `POST /proxy/{path...}`

Proxy routes are intended for GitHub and Microsoft Graph requests. Supported prefixes in the current code are:

- `/proxy/github/...`
- `/proxy/graph/...`

The request must include the `X-Proxy-Id` header. Coderunner looks up that value in Redis and uses the stored token for the upstream call.

Current implementation notes:

- Redis lookup is wired in and required.
- Target URL resolution is wired in for GitHub and Microsoft Graph.
- Proxy auth headers are prepared in code, but they are not currently attached to outbound requests because header forwarding is commented out in `core/common/requests.go`.
- `POST` bodies are parsed into the target model, but `RunProxyRequest` currently passes `nil` to the request sender, so outbound post bodies are not forwarded yet.

Because of those last two points, treat proxy support as partial/in-progress.

## MCP Server

The MCP server listens on `http://localhost:8081/mcp` using the streamable HTTP handler from `github.com/modelcontextprotocol/go-sdk/mcp`.

Currently registered tools:

- `github_list_user_repos`
- `github_list_user_pull_requests`

Only the GitHub MCP toolset is registered at startup right now. `graph.go` exists, but no Microsoft Graph MCP tools are currently exposed.

## Worker Communication

Coderunner talks to remote workers using the protobuf service in [`agent-proto/proto/agent.proto`](../agent-proto/proto/agent.proto).

Relevant RPCs:

- `Status`
- `ExecuteCode`
- `ExecuteCodeFresh`

In the current app flow:

- `/run` uses `ExecuteCode`
- `/status` uses `Status`
- worker selection is random across configured `REMOTE_HOSTS`

## Configuration

Configuration is loaded by `config.NewConfig()` from environment variables and `.env`.

Recognized variables:

- `REMOTE_HOSTS`: semicolon-separated gRPC worker addresses, for example `host1:50051;host2:50051`
- `APP_USER_NAME`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_USER`
- `REDIS_PASSWORD`
- `REDIS_DB`

Important current-state caveat:

- The Redis client in `app.NewApp()` is currently hardcoded to `localhost:6379` and DB `0`.
- Of the Redis env vars above, only `REDIS_PASSWORD` is actually applied when creating the client.

Telemetry uses the standard OpenTelemetry OTLP HTTP exporter configuration from the Go SDK defaults and environment.

## Build And Run

From the repository root:

```bash
make build-coderunner
make run-coderunner
```

Or directly:

```bash
cd coderunner
go build -o coderunner .
./coderunner
```

The built binary from the Make target is written to `./build/coderunner`.

## Development Notes

- The service is HTTP-based; it does not expose its own public gRPC server.
- Middleware currently wraps the HTTP API server, not the MCP server.
- The MCP server implementation identifies itself as `copilot` version `0.0.1`.
- The Dockerfile builds a static Linux binary and runs it from `scratch`.

## Testing

The package includes unit tests for proxy handler behavior in [`core/handlers/handlers_test.go`](./core/handlers/handlers_test.go).

In this sandbox, `go test ./...` currently fails because `httptest.NewServer` cannot bind a local port here. That is an environment limitation, not a README issue.

## License

This project is licensed under the MIT License. See [LICENSE](../LICENSE).
