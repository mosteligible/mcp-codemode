package main

import (
	"log"
	"log/slog"
	"net"

	"github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"github.com/mosteligible/mcp-codemode/agent/server"
	"google.golang.org/grpc"
)

func main() {
	listen, err := net.Listen("tcp", ":30031")
	if err != nil {
		log.Fatal(err.Error())
	}

	grpcServer := grpc.NewServer()
	pb.RegisterAgentServer(grpcServer, &server.Server{})
	slog.Info("Starting server on port: 30031")
	if err := grpcServer.Serve(listen); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
