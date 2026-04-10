package states

import (
	"bytes"
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/docker/docker/pkg/stdcopy"
	"github.com/moby/moby/api/types/container"
	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent/types"
)

const DefaultIdleContainerCleanupInterval = 300 // in seconds

type ContainerStatus struct {
	id         types.ContainerId
	imageName  string
	lastExecAt time.Time
	startedAt  time.Time
	sessionId  types.SessionId
	lock       *sync.RWMutex
}

func NewContainerStatus(containerClient *client.Client, sessionId types.SessionId, imageName string) (*ContainerStatus, error) {
	cs := &ContainerStatus{
		sessionId:  sessionId,
		imageName:  imageName,
		lastExecAt: time.Now(),
		startedAt:  time.Now(),
		lock:       &sync.RWMutex{},
	}
	containerId, err := cs.StartContainer(context.Background(), containerClient)
	if err != nil {
		slog.Error("error starting container", "error", err.Error())
		return nil, fmt.Errorf("could not start container")
	}
	slog.Info("container started", "container-id", containerId)
	cs.id = containerId
	return cs, nil
}

func (cs *ContainerStatus) StartContainer(
	ctx context.Context, containerClient *client.Client,
) (types.ContainerId, error) {
	newContainer, err := containerClient.ContainerCreate(
		ctx,
		client.ContainerCreateOptions{
			Config: &container.Config{
				Image: cs.imageName,
				Cmd:   []string{"sleep", "infinity"},
			},
			HostConfig: &container.HostConfig{
				Runtime: "runsc",
			},
		},
	)
	if err != nil {
		slog.Error("error creating container: " + err.Error())
		return "", err
	}

	if _, err := containerClient.ContainerStart(context.Background(), newContainer.ID, client.ContainerStartOptions{}); err != nil {
		slog.Error("error starting container: " + err.Error())
		return "", err
	}
	cs.id = types.ContainerId(newContainer.ID)
	cs.startedAt = time.Now()
	return cs.id, nil
}

func (cs *ContainerStatus) ExecuteCode(
	ctx context.Context, containerClient *client.Client, instruction string,
) (types.ExecuteResult, error) {
	slog.Info("executing code for container", "container-id", cs.id)
	result, err := containerClient.ExecCreate(
		ctx,
		string(cs.id),
		client.ExecCreateOptions{
			Cmd:          []string{"/bin/sh", "-c", instruction},
			AttachStdout: true,
			AttachStderr: true,
			TTY:          false,
		},
	)
	if err != nil {
		slog.Error("error executing code", "error", err.Error())
		return types.ExecuteResult{}, fmt.Errorf("error executing code")
	}

	attachResult, err := containerClient.ExecAttach(ctx, result.ID, client.ExecAttachOptions{TTY: false})
	if err != nil {
		slog.Error("error attaching to exec", "error", err.Error())
		return types.ExecuteResult{}, fmt.Errorf("error executing code")
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

	// TODO: this section needs to be made context aware to properly handle timeouts and cancellations
	if _, err := stdcopy.StdCopy(stdout, stderr, attachResult.Reader); err != nil {
		return types.ExecuteResult{}, fmt.Errorf("error copying output: %s", err.Error())
	}

	inspectResp, err := containerClient.ExecInspect(ctx, result.ID, client.ExecInspectOptions{})
	if err != nil {
		return types.ExecuteResult{}, fmt.Errorf("error inspecting exec instance: %s", err.Error())
	}

	cs.UpdateLastExecAt()
	return types.ExecuteResult{
		ExitCode: inspectResp.ExitCode,
		Stdout:   stdout.String(),
		Stderr:   stderr.String(),
	}, nil
}

func (cs *ContainerStatus) IsAvailable() bool {
	return cs.sessionId == ""
}

func (cs *ContainerStatus) UpdateLastExecAt() {
	cs.lock.Lock()
	defer cs.lock.Unlock()
	cs.lastExecAt = time.Now()
}

func (cs *ContainerStatus) StopContainer(containerClient *client.Client) error {
	cs.lock.Lock()
	defer cs.lock.Unlock()
	_, err := containerClient.ContainerStop(context.Background(), string(cs.id), client.ContainerStopOptions{})
	if err != nil {
		slog.Error("error stopping container", "container-id", cs.id, "error", err.Error())
		return err
	}
	return nil
}
