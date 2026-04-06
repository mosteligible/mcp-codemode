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

	"github.com/docker/docker/pkg/stdcopy"
	"github.com/moby/moby/api/types/container"
	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent/constants"
	"github.com/mosteligible/mcp-codemode/agent/core/common"
	"github.com/mosteligible/mcp-codemode/agent/types"
)

var bufferPool = sync.Pool{
	New: func() interface{} {
		b := bytes.Buffer{}
		return &b
	},
}

type ActiveContainers struct {
	Ids          []ContainerId
	containerMap map[ContainerId]ContainerStatus
	lock         sync.RWMutex
}

func NewActiveContainers(containerClient *client.Client, minActive int, imageName string) *ActiveContainers {
	ac := ActiveContainers{
		Ids:          []ContainerId{},
		containerMap: make(map[ContainerId]ContainerStatus),
	}
	ac.SetActiveContainers(containerClient, minActive, imageName)

	return &ac
}

func (c *ActiveContainers) Add(id ContainerId) {
	c.lock.Lock()
	defer c.lock.Unlock()
	c.Ids = append(c.Ids, id)
}

func (c *ActiveContainers) Remove(id ContainerId) {
	c.lock.Lock()
	defer c.lock.Unlock()
	for i, v := range c.Ids {
		if v == id {
			c.Ids = append(c.Ids[:i], c.Ids[i+1:]...)
			break
		}
	}
}

func (c *ActiveContainers) Count() int {
	c.lock.RLock()
	defer c.lock.RUnlock()
	return len(c.Ids)
}

func (c *ActiveContainers) Execute(
	ctx context.Context, containerClient *client.Client, instruction string, containerId ContainerId,
) (types.ExecuteResult, error) {
	if containerId != "" {
		return c.ExecuteInSession(ctx, containerClient, containerId, instruction)
	}
	// get random id from active containers
	c.lock.RLock()
	if len(c.Ids) == 0 {
		c.lock.RUnlock()
		return types.ExecuteResult{}, fmt.Errorf("no active containers available")
	}
	randindex := rand.Intn(len(c.Ids))
	containerID := c.Ids[randindex]
	c.lock.RUnlock()

	result, err := containerClient.ExecCreate(
		ctx,
		string(containerID),
		client.ExecCreateOptions{
			Cmd:          []string{"bash", "-c", instruction},
			AttachStdout: true,
			AttachStderr: true,
			TTY:          false,
		},
	)

	if err != nil {
		return types.ExecuteResult{}, fmt.Errorf("error executing code: %s", err.Error())
	}

	attachResult, err := containerClient.ExecAttach(ctx, result.ID, client.ExecAttachOptions{TTY: false})
	if err != nil {
		return types.ExecuteResult{}, fmt.Errorf("error attaching to exec instance: %s", err.Error())
	}
	defer attachResult.Close()

	select {
	case <-ctx.Done():
		return types.ExecuteResult{}, fmt.Errorf("execution timed out")
	default:
	}

	stdout := bufferPool.Get().(*bytes.Buffer)
	stderr := bufferPool.Get().(*bytes.Buffer)
	defer func() {
		stdout.Reset()
		stderr.Reset()
		bufferPool.Put(stderr)
		bufferPool.Put(stdout)
	}()

	if _, err := stdcopy.StdCopy(stdout, stderr, attachResult.Reader); err != nil {
		return types.ExecuteResult{}, fmt.Errorf("error copying output: %s", err.Error())
	}

	inspectResp, err := containerClient.ExecInspect(ctx, result.ID, client.ExecInspectOptions{})
	if err != nil {
		return types.ExecuteResult{}, fmt.Errorf("error inspecting exec instance: %s", err.Error())
	}

	return types.ExecuteResult{
		ExitCode: inspectResp.ExitCode,
		Stdout:   stdout.String(),
		Stderr:   stderr.String(),
	}, nil
}

func (c *ActiveContainers) ExecuteInSession(ctx context.Context, containerClient *client.Client, containerId ContainerId, instruction string) (types.ExecuteResult, error) {
	if _, exists := c.containerMap[containerId]; !exists {
		return types.ExecuteResult{}, fmt.Errorf("container with id %s not found in active containers", containerId)
	}
	return types.ExecuteResult{}, fmt.Errorf("session-based execution not implemented yet")
}

func (c *ActiveContainers) SetActiveContainers(containerClient *client.Client, minActive int, imageName string) {
	// run in a goroutine at intervals to update the active containers
	// where
	containers, err := common.GetActiveContainerIds(containerClient)
	if err != nil {
		slog.Error("error listing containers: " + err.Error())
		return
	}

	if len(containers) < minActive {
		slog.Info("active containers below minimum, creating new container")
		for range minActive - len(containers) {
			newContainer, err := containerClient.ContainerCreate(
				context.Background(),
				client.ContainerCreateOptions{
					Config: &container.Config{
						Image: imageName,
						Cmd:   []string{"sleep", "infinity"},
					},
					HostConfig: &container.HostConfig{
						Runtime: "runsc",
					},
				})
			if err != nil {
				slog.Error("error creating container: " + err.Error())
				continue
			}
			if _, err := containerClient.ContainerStart(context.Background(), newContainer.ID, client.ContainerStartOptions{}); err != nil {
				slog.Error("error starting container: " + err.Error())
				continue
			}
			containers = append(containers, newContainer.ID)
		}
	}

	currentContainers := []ContainerId{}
	containerMap := make(map[ContainerId]ContainerStatus)
	seenItems := 0
	for _, containerID := range containers {
		cid := (ContainerId)(containerID)
		currentContainers = append(currentContainers, cid)
		containerMap[cid] = ContainerStatus{id: cid}
		if _, exists := c.containerMap[cid]; exists {
			seenItems++
		}
	}
	if seenItems == len(currentContainers) {
		return
	}

	c.lock.Lock()
	defer c.lock.Unlock()
	c.Ids = currentContainers
	c.containerMap = containerMap
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

func (cs *ContainerState) StopActiveContainers(containerClient *client.Client) {
	containers, err := common.GetActiveContainerIds(containerClient)
	if err != nil {
		slog.Error("error listing containers: " + err.Error())
		return
	}

	for _, containerID := range containers {
		if _, err := containerClient.ContainerStop(context.Background(), containerID, client.ContainerStopOptions{}); err != nil {
			slog.Error("error stopping container: " + err.Error())
			continue
		}
		slog.Info("stopped container: " + containerID)
	}
}
