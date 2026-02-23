package app

import (
	"net/http"

	"github.com/mosteligible/mcp-codemode/coderunner/middlewares"
	"github.com/mosteligible/mcp-codemode/coderunner/states"
)

type App struct {
	wrapper             http.Handler
	port                string
	availableContainers states.ContainerState
}

func NewApp(port string) *App {
	app := &App{
		port:                port,
		availableContainers: *states.NewContainerState(),
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
