package app

import (
	"log/slog"
	"net/http"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/mosteligible/mcp-codemode/coderunner/core/tools"
)

type McpApp struct {
	server *mcp.Server
	logger *slog.Logger
}

func NewMcpApp(logger *slog.Logger) *McpApp {
	implementation := &mcp.Implementation{
		Name:    "copilot",
		Title:   "Copilot",
		Version: "0.0.1",
	}

	serverOpts := &mcp.ServerOptions{
		Logger:    logger,
		KeepAlive: 30 * time.Second,
	}

	server := mcp.NewServer(implementation, serverOpts)
	return &McpApp{server: server, logger: logger}
}

func (app *McpApp) Start() error {
	tools.NewGithubTool(app.server)

	handler := mcp.NewStreamableHTTPHandler(
		func(r *http.Request) *mcp.Server {
			return app.server
		},
		&mcp.StreamableHTTPOptions{
			Stateless:    true,
			JSONResponse: true,
		},
	) // what to do here, I don't understand its usage
	mux := http.NewServeMux()
	mux.Handle("/mcp", handler)
	app.logger.Info("starting mcp server on port :8081")
	return http.ListenAndServe(":8081", handler)
}
