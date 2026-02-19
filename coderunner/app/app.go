package app

import (
	"net/http"

	"github.com/mosteligible/mcp-codemode/coderunner/middlewares"
)

type App struct {
	wrapper             http.Handler
	port                string
	availableContainers []string
}

func NewApp(port string) *App {
	app := &App{
		port: port,
	}
	app.init()
	return app
}

func (a *App) init() {
	mux := http.NewServeMux()

	a.wrapper = middlewares.LoggingMiddleware(mux)
}

func (a *App) Start() error {
	return http.ListenAndServe(
		a.port, a.wrapper,
	)
}
