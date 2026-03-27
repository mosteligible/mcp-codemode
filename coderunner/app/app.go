package app

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"math/rand"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/mosteligible/mcp-codemode/coderunner/config"
	"github.com/mosteligible/mcp-codemode/coderunner/constants"
	"github.com/mosteligible/mcp-codemode/coderunner/core/common"
	"github.com/mosteligible/mcp-codemode/coderunner/core/handlers"
	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
	workerclient "github.com/mosteligible/mcp-codemode/coderunner/core/worker_client"
	"github.com/mosteligible/mcp-codemode/coderunner/middlewares"
	"github.com/redis/go-redis/v9"
)

type App struct {
	wrapper         http.Handler
	port            string
	appConfig       *config.Config
	redisClient     *redis.Client
	requestClient   *http.Client
	grpcConnections map[string]*workerclient.WorkerClient
}

func NewApp(port string) *App {
	conf := config.NewConfig()
	redisOpts := &redis.Options{
		Addr: "localhost:6379",
		DB:   0,
	}
	if conf.RedisPassword != "" {
		redisOpts.Password = conf.RedisPassword
	}
	slog.Info("starting redis client")
	redisClient := redis.NewClient(redisOpts)

	grpcConnections := make(map[string]*workerclient.WorkerClient)
	slog.Info("remote hosts: " + strings.Join(conf.RemoteHosts, ", "))
	for _, host := range conf.RemoteHosts {
		conn, err := workerclient.NewWorkerClient(host)
		if err != nil {
			slog.Error("could not connect to worker at:" + host)
			continue
		}
		slog.Info("connected to host: " + host)
		grpcConnections[host] = conn
	}

	app := &App{
		port:        port,
		appConfig:   conf,
		redisClient: redisClient,
		requestClient: &http.Client{
			Timeout: 180 * time.Second,
		},
		grpcConnections: grpcConnections,
	}

	app.init()
	return app
}

func (a *App) init() {
	mux := http.NewServeMux()

	mux.HandleFunc("/run", a.RunCode)
	mux.HandleFunc("GET /proxy/{path...}", a.Proxy)
	mux.HandleFunc("POST /proxy/{path...}", a.Proxy)
	mux.HandleFunc("/status", a.status)
	a.wrapper = middlewares.LoggingMiddleware(mux)
}

func (a *App) Start() error {
	return http.ListenAndServe(
		a.port, a.wrapper,
	)
}

func (a *App) status(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]int16{"status": 200})
}

func (a *App) RunCode(w http.ResponseWriter, r *http.Request) {
	var codeRequest types.CodeRunnerRequest

	err := json.NewDecoder(r.Body).Decode(&codeRequest)
	if err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	randIndex := rand.Intn(len(a.grpcConnections))
	conn := a.grpcConnections[a.appConfig.RemoteHosts[randIndex]]
	output := common.ExecuteCommand(conn, codeRequest.Code, codeRequest.Language)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(output)

}

func (a *App) Proxy(w http.ResponseWriter, r *http.Request) {
	correlationID := uuid.New().String()
	proxyId := r.Header.Get(constants.PROXY_HEADER_KEY)
	proxyId = strings.TrimSpace(proxyId)
	if proxyId == "" {
		http.Error(w, "Missing proxy ID", http.StatusBadRequest)
		return
	}

	target, err := common.GetTarget(r, correlationID)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(common.GetErrorResponseMessage(
			fmt.Sprintf("Invalid error path - %s", err.Error()),
		))
		return
	}
	slog.Info(
		"sending proxy request",
		"url", target.Url,
		"method", target.Method,
		"correlation_id", correlationID,
	)

	token := a.redisClient.Get(r.Context(), proxyId)
	if token.Err() != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(common.GetErrorResponseMessage("invalid proxy id"))
		return
	}
	target.Token = token.Val()

	apiResponse, err := handlers.RunProxyRequest(target, a.requestClient, correlationID)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(common.GetErrorResponseMessage("error processing proxy request"))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(apiResponse)
}
