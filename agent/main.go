package main

import (
	"context"
	"log"
	"log/slog"
	"net"

	"github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/emptypb"
)

type Server struct {
	pb.UnimplementedAgentServer
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

func main() {
	listen, err := net.Listen("tcp", ":30031")
	if err != nil {
		log.Fatal(err.Error())
	}

	grpcServer := grpc.NewServer()
	pb.RegisterAgentServer(grpcServer, &Server{})
	slog.Info("Starting server on port: 30031")
	if err := grpcServer.Serve(listen); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
