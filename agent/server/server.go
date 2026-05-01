package server

import (
	"context"
	"log"
	"log/slog"
	"time"

	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"github.com/mosteligible/mcp-codemode/agent/config"
	"github.com/mosteligible/mcp-codemode/agent/core"
	"github.com/mosteligible/mcp-codemode/agent/core/common"
	"github.com/mosteligible/mcp-codemode/agent/heartbeat"
	"github.com/mosteligible/mcp-codemode/agent/states"
	"github.com/mosteligible/mcp-codemode/agent/types"
	"github.com/redis/go-redis/v9"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
	"go.opentelemetry.io/otel/trace/noop"
	"google.golang.org/protobuf/types/known/emptypb"
)

type Server struct {
	pb.UnimplementedAgentServer
	containerState  *states.ContainerState
	containerClient *client.Client
	config          *config.Config
	redisClient     *redis.Client
}

// NewServer initializes the Docker-backed execution state used by the gRPC service.
func NewServer(shutdownSignal chan struct{}, redisClient *redis.Client) *Server {
	slog.Info("starting server")
	conf := config.NewConfig()
	dockerClient, err := client.New(
		client.FromEnv,
		client.WithTraceProvider(noop.NewTracerProvider()),
	)
	if err != nil {
		log.Fatal("could not create docker client: ", err.Error())
	}

	if !core.CheckDockerAvailable(dockerClient) {
		log.Fatal("docker is not available, setup docker first: https://docs.docker.com/get-docker/")
	}

	slog.Info("docker found, starting server")
	containerState := states.NewContainerState(
		dockerClient, conf.DockerImageName, conf.MinActiveContainers, conf.MaxActiveContainers,
	)

	beats := heartbeat.NewBeat(conf, containerState)
	go beats.Start(redisClient, shutdownSignal)

	return &Server{
		containerState:  containerState,
		containerClient: dockerClient,
		config:          conf,
		redisClient:     redisClient,
	}
}

// Status returns a lightweight health response for liveness and readiness checks.
func (s *Server) Status(ctx context.Context, in *emptypb.Empty) (*pb.HealthStatus, error) {
	return &pb.HealthStatus{
		Code:    0,
		Message: "healthy",
	}, nil
}

// ExecuteCode validates the request, applies a fixed timeout, and runs the code in a managed container.
func (s *Server) ExecuteCode(
	ctx context.Context, in *pb.ExecuteCodeRequest,
) (*pb.ExecuteCodeResponse, error) {
	if err := common.ValidateProgrammingLanguage(in.Language); err != nil {
		return &pb.ExecuteCodeResponse{
			ExitCode: 2,
			Output:   "",
			Error:    err.Error(),
		}, nil
	}

	const maxExecutionTime = 30 * time.Second
	timeoutContext, cancel := context.WithTimeout(ctx, maxExecutionTime)
	defer cancel()
	trace.SpanFromContext(timeoutContext).SetAttributes(
		attribute.String("code.instruction", in.Instruction),
		attribute.String("code.language", in.Language),
	)
	slog.Info("received code", "instruction", in.Instruction, "language", in.Language)
	result, err := s.containerState.Execute(
		timeoutContext, s.containerClient, in.Instruction, types.SessionId(in.SessionId),
	)
	if err != nil {
		return &pb.ExecuteCodeResponse{
			ExitCode: 2,
			Output:   "",
			Error:    err.Error(),
		}, nil
	}
	slog.Info(
		"processed Code", "result", result.Stdout, "error", result.Stderr, "exitCode", result.ExitCode,
	)
	return &pb.ExecuteCodeResponse{
		ExitCode: int32(result.ExitCode),
		Output:   result.Stdout,
		Error:    result.Stderr,
	}, nil
}

// HandleShutdown stops managed containers before the process exits.
func (s *Server) HandleShutdown() {
	slog.Info("shutting down server, cleaning up containers...")
	s.containerState.StopActiveContainers(s.containerClient)
	slog.Info("all containers cleaned up, shutting down server")
}
