package main

import (
	"context"
	"log"
	"log/slog"

	"github.com/mosteligible/mcp-codemode/coderunner/app"
	"github.com/mosteligible/mcp-codemode/coderunner/core/telemetry"
)

func main() {
	ctx := context.Background()
	shutdown, err := telemetry.InitTracer(ctx, "go-codemode")
	if err != nil {
		log.Fatalf("failed to initialize telemetry: %v", err)
	}
	defer shutdown(ctx)

	codeRunnerApp := app.NewApp(":8080")
	slog.Info("starting server on port " + ":8080")
	go codeRunnerApp.Start()
	logger := slog.New(slog.NewTextHandler(log.Writer(), nil))
	mcpApp := app.NewMcpApp(logger)
	mcpApp.Start()
}
