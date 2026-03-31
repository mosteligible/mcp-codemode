package app

import (
	"context"
	"log/slog"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/mosteligible/mcp-codemode/pkg/tools"
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
	app.logger.Info("starting mcp server.")
	return app.server.Run(context.Background(), &mcp.StreamableServerTransport{})
}
