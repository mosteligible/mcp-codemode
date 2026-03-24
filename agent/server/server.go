package server

import (
	"context"
	"log"
	"log/slog"
	"time"

	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"github.com/mosteligible/mcp-codemode/agent/core"
	"github.com/mosteligible/mcp-codemode/agent/states"
	"google.golang.org/protobuf/types/known/emptypb"
)

type Server struct {
	pb.UnimplementedAgentServer
	containerState  *states.ContainerState
	containerClient *client.Client
}

func NewServer(containerImageName string, minActive int) *Server {
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
	containerState := states.NewContainerState(dockerClient, containerImageName, minActive)

	go func() {
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			containerState.Containers.SetActiveContainers(dockerClient)
		}
	}()

	return &Server{
		containerState:  containerState,
		containerClient: dockerClient,
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
