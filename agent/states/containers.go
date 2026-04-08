package states

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"log/slog"
	"math/rand"
	"sync"
	"time"

	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent/constants"
	"github.com/mosteligible/mcp-codemode/agent/types"
)

var bufferPool = sync.Pool{
	New: func() interface{} {
		b := bytes.Buffer{}
		return &b
	},
}

type ActiveContainers struct {
	containerMap          map[types.ContainerId]*ContainerStatus
	sessionToContainerMap map[types.SessionId]types.ContainerId
	lock                  sync.RWMutex
}

func NewActiveContainers(containerClient *client.Client, minActive int, imageName string) *ActiveContainers {
	ac := ActiveContainers{
		containerMap:          make(map[types.ContainerId]*ContainerStatus),
		sessionToContainerMap: make(map[types.SessionId]types.ContainerId),
	}

	return &ac
}

func (c *ActiveContainers) Remove(id types.ContainerId) {
	c.lock.Lock()
	defer c.lock.Unlock()
	delete(c.containerMap, id)
}

func (c *ActiveContainers) Count() int {
	c.lock.RLock()
	defer c.lock.RUnlock()
	return len(c.containerMap)
}

func (c *ActiveContainers) Execute(
	ctx context.Context, containerClient *client.Client, instruction string, containerId types.ContainerId, sessionId types.SessionId,
) (types.ExecuteResult, error) {
	if containerId != "" {
		return c.ExecuteInSession(ctx, containerClient, sessionId, instruction)
	}
	// get random id from active containers
	c.lock.RLock()
	if len(c.containerMap) == 0 {
		c.lock.RUnlock()
		return types.ExecuteResult{}, fmt.Errorf("no active containers available")
	}
	keys := make([]types.ContainerId, 0, len(c.containerMap))
	for k := range c.containerMap {
		keys = append(keys, k)
	}
	randindex := rand.Intn(len(keys))
	containerID := keys[randindex]
	c.lock.RUnlock()

	containerStatus := c.containerMap[containerID]
	return containerStatus.ExecuteCode(ctx, containerClient, instruction)
}

func (c *ActiveContainers) ExecuteInSession(
	ctx context.Context, containerClient *client.Client, sessionId types.SessionId, instruction string,
) (types.ExecuteResult, error) {
	containerId, exists := c.sessionToContainerMap[sessionId]
	if !exists {
		return types.ExecuteResult{}, fmt.Errorf("container with id %s not found in active containers", sessionId)
	}

	containerStatus := c.containerMap[containerId]
	return containerStatus.ExecuteCode(ctx, containerClient, instruction)
}

type ContainerState struct {
	containerImageName  string
	MinActive           int
	ProgrammingLanguage string
	Containers          *ActiveContainers
}

func NewContainerState(containerClient *client.Client, imageName string, minActive int) *ContainerState {
	if imageName == "" {
		imageName = constants.DefaultDockerImageName
	}
	if containerClient == nil {
		log.Fatalf("container client provided is nil!")
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(120*time.Second))
	defer cancel()
	slog.Info("pulling docker image: " + imageName)
	result, err := containerClient.ImagePull(ctx, imageName, client.ImagePullOptions{})
	if err != nil {
		log.Fatalf("failed to pull docker image: %v", err)
	}
	defer result.Close()

	err = result.Wait(ctx)
	if err != nil {
		log.Fatalf("failed to wait for image pull: %v", err)
	}

	slog.Info(
		"pulled from container registry",
		"imageName", imageName,
	)

	return &ContainerState{
		containerImageName: imageName,
		MinActive:          minActive,
		Containers:         NewActiveContainers(containerClient, minActive, imageName),
	}
}

func (cs *ContainerState) StartContainer(containerClient *client.Client, sessionId types.SessionId) (types.ContainerId, error) {
	containerStatus := NewContainerStatus(containerClient, sessionId)
	return containerStatus.id, nil
}

func (cs *ContainerState) StartContainerForUserSession(containerClient *client.Client, sessionId string) {
	containerId, err := cs.StartContainer(containerClient, types.SessionId(sessionId))
	if err != nil {
		slog.Error("error starting container for user session", "sessionId", sessionId, "error", err.Error())
		return
	}
	slog.Info("started container for user session", "sessionId", sessionId, "containerId", containerId)
}

func (cs *ContainerState) StopActiveContainers(containerClient *client.Client) {
	for containerID := range cs.Containers.containerMap {
		if _, err := containerClient.ContainerStop(context.Background(), string(containerID), client.ContainerStopOptions{}); err != nil {
			slog.Error("error stopping container: " + err.Error())
			continue
		}
		cs.Containers.Remove(types.ContainerId(containerID))
		slog.Info("stopped container: " + string(containerID))
	}
}

func (cs *ContainerState) CleanupIdleContainers(containerClient *client.Client, idleInterval int) {
	for id, status := range cs.Containers.containerMap {
		if time.Since(status.lastExecAt).Seconds() > float64(idleInterval) {
			slog.Info("cleaning up idle container", "containerId", id)
			if _, err := containerClient.ContainerStop(context.Background(), string(id), client.ContainerStopOptions{}); err != nil {
				slog.Error("error stopping container: " + err.Error())
				continue
			}
			slog.Info("stopped idle container: " + string(id))
			cs.Containers.Remove(id)
		}
	}
}
