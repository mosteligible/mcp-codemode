package server

import (
	"context"
	"log"

	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"github.com/mosteligible/mcp-codemode/agent/states"
	"google.golang.org/protobuf/types/known/emptypb"
)

type Server struct {
	pb.UnimplementedAgentServer
	containerStates *states.ContainerState
	containerClient *client.Client
}

func NewServer(containerImageName string, minActive int) *Server {
	dockerClient, err := client.New(
		client.FromEnv,
	)
	if err != nil {
		log.Fatal("could not create docker client: ", err.Error())
	}

	return &Server{
		containerStates: states.NewContainerState(dockerClient, containerImageName, minActive),
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
	return &pb.ExecuteCodeResponse{
		ExitCode: 0,
		Output:   "Hello, World!\n",
		Error:    "",
	}, nil
}
