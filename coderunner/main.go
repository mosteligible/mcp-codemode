package main

import (
	"log/slog"

	"github.com/mosteligible/mcp-codemode/coderunner/app"
)

func main() {
	app := app.NewApp(":8080")
	slog.Info("starting server on port " + ":8080")
	app.Start()
}
