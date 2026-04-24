package workerclient

import (
	"context"
	"log/slog"

	pb "github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"github.com/redis/go-redis/v9"
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

type WorkerConnections struct {
	Connections      map[string]*WorkerClient
	sessionToHostMap map[string]string
}

func (wc *WorkerConnections) GetClientForHost(host string) (*WorkerClient, bool) {
	client, ok := wc.Connections[host]
	return client, ok
}

func (wc *WorkerConnections) CloseAll() {
	for _, client := range wc.Connections {
		client.conn.Close()
	}
}

func (wc *WorkerConnections) AddClientForHost(host string, client *WorkerClient) {
	wc.Connections[host] = client
}

func (wc *WorkerConnections) RemoveWorkerHost(ctx context.Context, host string, redisClient *redis.Client) {
	delete(wc.Connections, host)
	if redisClient == nil {
		for sessionId, sessionhost := range wc.sessionToHostMap {
			if host == sessionhost {
				delete(wc.sessionToHostMap, sessionId)
			}
		}
		return
	}

	redisClient.JSONDel(ctx, host, ".")
}

func (wc *WorkerConnections) RemoveUserSessionFromHost(ctx context.Context, host, sessionId string, redisClient *redis.Client) {
	if redisClient == nil {
		delete(wc.sessionToHostMap, sessionId)
		return
	}

	redisClient.JSONDel(ctx, host, sessionId)
}

func (wc *WorkerConnections) AddUserSessionToHost(ctx context.Context, host, sessionId string, redisClient *redis.Client) error {
	if redisClient == nil {
		slog.Warn("using in-memory map for control planing of user session")
		wc.sessionToHostMap[sessionId] = host
		return nil
	}

	redisClient.JSONSet(ctx, host, sessionId, struct{}{})
	return nil
}
