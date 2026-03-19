package states

import (
	"context"
	"log"
	"time"

	"github.com/moby/moby/client"
)

type ContainerId string
type Containers map[ContainerId]bool

func (c Containers) Add(id ContainerId) {
	c[id] = true
}

type ContainerState struct {
	containerImageName  string
	MinActive           int
	ProgrammingLanguage string
	containers          Containers
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
		containers:         make(Containers),
	}
}

func (cs *ContainerState) CheckActiveContainers() {}
