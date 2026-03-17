package workerclient

import (
	pb "github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"google.golang.org/grpc"
)

type WorkerClient struct {
	conn   *grpc.ClientConn
	client pb.AgentClient
}
