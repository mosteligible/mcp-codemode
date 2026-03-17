package workerclient

import (
	pb "github.com/mosteligible/mcp-codemode/coderunner/agent-proto"
	"google.golang.org/grpc"
)

type WorkerClient struct {
	conn   *grpc.ClientConn
	client pb.AgentClient
}
