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

func (c *ActiveContainers) Add(containerStatus *ContainerStatus) {
	c.lock.Lock()
	defer c.lock.Unlock()
	c.containerMap[containerStatus.id] = containerStatus
	c.sessionToContainerMap[containerStatus.sessionId] = containerStatus.id
}

func (c *ActiveContainers) Remove(sessionId types.SessionId) {
	c.lock.Lock()
	defer c.lock.Unlock()
	containerId, exists := c.sessionToContainerMap[sessionId]
	if !exists {
		return
	}
	delete(c.containerMap, containerId)
	delete(c.sessionToContainerMap, sessionId)
}

func (c *ActiveContainers) Count() int {
	c.lock.RLock()
	defer c.lock.RUnlock()
	return len(c.containerMap)
}

func (c *ActiveContainers) Execute(
	ctx context.Context, containerClient *client.Client, instruction string, sessionId types.SessionId, imageName string,
) (types.ExecuteResult, error) {
	slog.Info("executing code", "sessionId", sessionId)
	if sessionId != "" {
		return c.ExecuteInSession(ctx, containerClient, sessionId, instruction, imageName)
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
	ctx context.Context, containerClient *client.Client, sessionId types.SessionId, instruction, imageName string,
) (types.ExecuteResult, error) {
	slog.Info("executing in session", "sessionId", sessionId)
	var containerStatus *ContainerStatus
	containerId, exists := c.sessionToContainerMap[sessionId]
	if !exists {
		slog.Info("no active container for session, starting new container", "sessionId", sessionId)
		containerStatus = NewContainerStatus(containerClient, sessionId, imageName)
		c.containerMap[containerId] = containerStatus
		c.sessionToContainerMap[sessionId] = containerId
	} else {
		containerStatus = c.containerMap[containerId]
	}

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

	cs := &ContainerState{
		containerImageName: imageName,
		MinActive:          minActive,
		Containers:         NewActiveContainers(containerClient, minActive, imageName),
	}

	// goroutine to garbage collect idle containers every 60 seconds; idle time 60 seconds
	go func() {
		ticker := time.NewTicker(60 * time.Second)
		for {
			<-ticker.C
			slog.Info("running idle container cleanup")
			cs.CleanupIdleContainers(containerClient, 60*8) // idle interval of 8 minutes
		}
	}()

	return cs
}

func (cs *ContainerState) Execute(
	ctx context.Context, containerClient *client.Client, instruction string, sessionId types.SessionId,
) (types.ExecuteResult, error) {
	return cs.Containers.Execute(ctx, containerClient, instruction, sessionId, cs.containerImageName)
}

func (cs *ContainerState) StartContainer(containerClient *client.Client, sessionId types.SessionId) (types.ContainerId, error) {
	containerStatus := NewContainerStatus(containerClient, sessionId, cs.containerImageName)
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
	for sessionId, containerId := range cs.Containers.sessionToContainerMap {
		if _, err := containerClient.ContainerStop(context.Background(), string(containerId), client.ContainerStopOptions{}); err != nil {
			slog.Error("error stopping container: " + err.Error())
			continue
		}
		cs.Containers.Remove(types.SessionId(sessionId))
		slog.Info("stopped container: " + string(containerId))
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
			cs.Containers.Remove(types.SessionId(status.sessionId))
		}
	}
}
