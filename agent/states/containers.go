package states

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/docker/docker/pkg/stdcopy"
	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent/types"
)

var bufferPool = sync.Pool{
	New: func() interface{} {
		b := bytes.Buffer{}
		return &b
	},
}

type ContainerId string
type ActiveContainers map[ContainerId]bool

func (c ActiveContainers) Add(id ContainerId) {
	c[id] = true
}

func (c ActiveContainers) Remove(id ContainerId) {
	delete(c, id)
}

func (c ActiveContainers) Count() int {
	return len(c)
}

func (c ActiveContainers) Execute(ctx context.Context, containerClient *client.Client, instruction string) (types.ExecuteResult, error) {
	result, err := containerClient.ExecCreate(
		ctx,
		"placeholder",
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

	return types.ExecuteResult{
		ExitCode: 0,
		Stdout:   stdout.String(),
		Stderr:   stderr.String(),
	}, nil
}

type ContainerState struct {
	containerImageName  string
	MinActive           int
	ProgrammingLanguage string
	Containers          ActiveContainers
}

func NewContainerState(containerClient *client.Client, imageName string, minActive int) *ContainerState {
	if imageName == "" {
		imageName = "python:3.14-slim"
	}
	if containerClient == nil {
		log.Fatalf("container client provided is nil!")
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(120*time.Second))
	defer cancel()
	containerClient.ImagePull(ctx, imageName, client.ImagePullOptions{})
	return &ContainerState{
		containerImageName: imageName,
		MinActive:          minActive,
		Containers:         make(ActiveContainers),
	}
}

func (cs *ContainerState) CheckActiveContainers() {}
