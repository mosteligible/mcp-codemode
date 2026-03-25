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
	"github.com/mosteligible/mcp-codemode/agent/states"
	"google.golang.org/protobuf/types/known/emptypb"
)

type Server struct {
	pb.UnimplementedAgentServer
	containerState  *states.ContainerState
	containerClient *client.Client
	config          *config.Config
}

func NewServer(shutdownSignal chan struct{}) *Server {
	slog.Info("starting server")
	conf := config.NewConfig()
	dockerClient, err := client.New(
		client.FromEnv,
	)
	if err != nil {
		log.Fatal("could not create docker client: ", err.Error())
	}

	if !core.CheckDockerAvailable(dockerClient) {
		log.Fatal("docker is not available, setup docker first: https://docs.docker.com/get-docker/")
	}

	slog.Info("docker found, starting server")
	containerState := states.NewContainerState(dockerClient, conf.DockerImageName, conf.MinActive)

	go func() {
		ticker := time.NewTicker(time.Duration(conf.ActiveContainerCheckInterval) * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				slog.Info("setting minimum active containers")
				containerState.Containers.SetActiveContainers(dockerClient, conf.MinActive, conf.DockerImageName)
			case <-shutdownSignal:
				return
			}

		}
	}()

	return &Server{
		containerState:  containerState,
		containerClient: dockerClient,
		config:          conf,
	}
}

func (s *Server) Status(ctx context.Context, in *emptypb.Empty) (*pb.HealthStatus, error) {
	return &pb.HealthStatus{
		Code:    0,
		Message: "healthy",
	}, nil
}

func (s *Server) ExecuteCode(ctx context.Context, in *pb.ExecuteCodeRequest) (*pb.ExecuteCodeResponse, error) {
	const maxExecutionTime = 30 * time.Second
	timeoutContext, cancel := context.WithTimeout(ctx, maxExecutionTime)
	defer cancel()
	slog.Info("received code", "instruction", in.Instruction, "language", in.Language)
	result, err := s.containerState.Containers.Execute(timeoutContext, s.containerClient, in.Instruction)
	if err != nil {
		return &pb.ExecuteCodeResponse{
			ExitCode: 2,
			Output:   "",
			Error:    err.Error(),
		}, nil
	}
	return &pb.ExecuteCodeResponse{
		ExitCode: int32(result.ExitCode),
		Output:   result.Stdout,
		Error:    result.Stderr,
	}, nil
}

func (s *Server) HandleShutdown() {
	slog.Info("shutting down server, cleaning up containers...")
	s.containerState.StopActiveContainers(s.containerClient)
}
