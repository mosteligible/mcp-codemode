package main

import (
	"context"
	"log"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"syscall"

	"github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"github.com/mosteligible/mcp-codemode/agent/config"
	"github.com/mosteligible/mcp-codemode/agent/core/interceptors"
	"github.com/mosteligible/mcp-codemode/agent/server"
	"github.com/mosteligible/mcp-codemode/agent/telemetry"
	"google.golang.org/grpc"
)

func main() {
	ctx := context.Background()
	conf := config.NewConfig()
	listen, err := net.Listen("tcp", conf.WorkerPort)
	if err != nil {
		log.Fatal(err.Error())
	}

	shutdown, err := telemetry.InitTracer(ctx, "codemode-agent")
	if err != nil {
		log.Fatal(err.Error())
	}
	defer shutdown(ctx)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	shutdownSignal := make(chan struct{})
	gserver := server.NewServer(shutdownSignal)
	serverErr := make(chan error, 1)
	go func() {
		grpcServer := grpc.NewServer(grpc.ChainUnaryInterceptor(
			interceptors.UnaryInterceptorLogger,
		))
		defer grpcServer.GracefulStop()
		pb.RegisterAgentServer(grpcServer, gserver)
		slog.Info("Starting server on port " + conf.WorkerPort)
		if err := grpcServer.Serve(listen); err != nil {
			serverErr <- err
		}
	}()

	select {
	case <-ctx.Done():
		slog.Info("Shutting down server...")
		close(shutdownSignal)
		gserver.HandleShutdown()
	case err := <-serverErr:
		gserver.HandleShutdown()
		log.Fatalf("Server error: %v", err)
	}
}
