package app

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/mosteligible/mcp-codemode/coderunner/config"
	"github.com/mosteligible/mcp-codemode/coderunner/constants"
	"github.com/mosteligible/mcp-codemode/coderunner/core/common"
	"github.com/mosteligible/mcp-codemode/coderunner/core/handlers"
	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
	"github.com/mosteligible/mcp-codemode/coderunner/middlewares"
	"github.com/mosteligible/mcp-codemode/coderunner/states"
	"github.com/redis/go-redis/v9"
)

type App struct {
	wrapper             http.Handler
	port                string
	redisClient         *redis.Client
	availableContainers states.ContainerState
	requestClient       *http.Client
}

func NewApp(port string) *App {
	fmt.Println(config.Conf)
	redisOpts := &redis.Options{
		Addr: "localhost:6379",
		DB:   0,
	}
	if config.Conf.RedisPassword != "" {
		redisOpts.Password = config.Conf.RedisPassword
	}
	redisClient := redis.NewClient(redisOpts)

	app := &App{
		port:                port,
		availableContainers: *states.NewContainerState(),
		redisClient:         redisClient,
		requestClient: &http.Client{
			Timeout: 180 * time.Second,
		},
	}

	app.init()
	return app
}

func (a *App) init() {
	mux := http.NewServeMux()

	mux.HandleFunc("/run", a.RunCode)
	mux.HandleFunc("/proxy", a.Proxy)
	a.wrapper = middlewares.LoggingMiddleware(mux)
}

func (a *App) Start() error {
	return http.ListenAndServe(
		a.port, a.wrapper,
	)
}

func (a *App) RunCode(w http.ResponseWriter, r *http.Request) {
	var codeRequest types.CodeRunnerRequest

	err := json.NewDecoder(r.Body).Decode(&codeRequest)
	if err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	output := common.ExecuteCommand(codeRequest.Code)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(output)

}

func (a *App) Proxy(w http.ResponseWriter, r *http.Request) {
	proxyId := r.Header.Get(constants.PROXY_HEADER_KEY)
	proxyId = strings.TrimSpace(proxyId)
	if proxyId == "" {
		http.Error(w, "Missing proxy ID", http.StatusBadRequest)
		return
	}

	path := r.URL.Path
	target, err := common.GetUrlFromProxyPath(path, r.Method)
	if err != nil {
		http.Error(w, "Invalid proxy path", http.StatusBadRequest)
		return
	}
	token := a.redisClient.Get(r.Context(), proxyId)
	if token.Err() != nil {
		http.Error(w, "Invalid proxy ID", http.StatusUnauthorized)
		return
	}

	apiResponse, err := handlers.RunProxyRequest(target, a.requestClient)
	if err != nil {
		http.Error(w, "Error processing proxy request", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(apiResponse)
}
