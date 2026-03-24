package core

import (
	"context"
	"time"

	"github.com/moby/moby/client"
)

func CheckDockerAvailable(dockerClient *client.Client) bool {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, err := dockerClient.Ping(ctx, client.PingOptions{})
	return err == nil
}
