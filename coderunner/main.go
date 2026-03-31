package main

import (
	"log"
	"log/slog"

	"github.com/mosteligible/mcp-codemode/coderunner/app"
)

func main() {
	codeRunnerApp := app.NewApp(":8080")
	slog.Info("starting server on port " + ":8080")
	go codeRunnerApp.Start()
	logger := slog.New(slog.NewTextHandler(log.Writer(), nil))
	mcpApp := app.NewMcpApp(logger)
	mcpApp.Start()
}
