package states

import (
	"log/slog"
	"math/rand"
	"os/exec"
	"strings"
	"sync"
	"time"
)

type ContainerState struct {
	Ids            []string
	readWriteMutex *sync.RWMutex
}

func NewContainerState() *ContainerState {
	cs := &ContainerState{
		Ids:            []string{},
		readWriteMutex: &sync.RWMutex{},
	}

	// for a container state, we need to periodically update the available containers
	// so there are no stale containers in the list. run a goroutine to update the available
	// containers every 10 seconds
	go func() {
		for {
			err := cs.SetAvailableContainers()
			if err != nil {
				slog.Error("Failed to set available containers", "error", err)
			} else {
				slog.Info("Successfully updated available containers")
			}
			time.Sleep(10 * time.Second)
		}
	}()
	return cs
}

func (s *ContainerState) GetAContainer() string {
	s.readWriteMutex.RLock()
	defer s.readWriteMutex.RUnlock()
	if len(s.Ids) == 0 {
		return ""
	}
	index := rand.Intn(len(s.Ids))
	return s.Ids[index]
}

func (s *ContainerState) SetAvailableContainers() error {
	// reads the list of running docker containers and updates the list of available containers
	// reads the containers with command `docker ps --format "{{.ID}}"` and updates the list of available containers
	// for simplicity, we will just generate some random container ids here
	s.readWriteMutex.Lock()
	defer s.readWriteMutex.Unlock()
	result := exec.Command(
		"bash", "-c", "docker ps --format \"{{.ID}}\"",
	)
	output, err := result.Output()
	if err != nil {
		return err
	}

	// split the output by newlines and update the list of available containers
	stdout := string(output)
	lines := strings.Split(stdout, "\n")
	s.Ids = []string{}
	for _, line := range lines {
		if line != "" {
			s.Ids = append(s.Ids, line)
		}
	}
	return nil
}
