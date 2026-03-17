package workerclient

import (
	pb "github.com/mosteligible/mcp-codemode/agent-proto/pb"
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
