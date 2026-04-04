package workerclient

import (
	pb "github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type WorkerClient struct {
	conn   *grpc.ClientConn
	Client pb.AgentClient
}

func NewWorkerClient(address string) (*WorkerClient, error) {
	conn, err := grpc.NewClient(address, grpc.WithTransportCredentials(
		insecure.NewCredentials(),
	), grpc.WithStatsHandler(
		otelgrpc.NewClientHandler(),
	))
	if err != nil {
		return nil, err
	}
	client := pb.NewAgentClient(conn)
	return &WorkerClient{
		conn:   conn,
		Client: client,
	}, nil
}
