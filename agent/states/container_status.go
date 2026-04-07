package states

import (
	"fmt"
	"time"
)

const DefaultIdleContainerCleanupInterval = 300 // in seconds

type ContainerId string

type ContainerStatus struct {
	id         ContainerId
	lastExecAt time.Time
	startedAt  time.Time
	sessionId  string
}

func (cs *ContainerStatus) IsAvailable() bool {
	return cs.sessionId == ""
}

func (cs *ContainerStatus) AddSession(sessionId string) error {
	if cs.sessionId != "" {
		return fmt.Errorf("container is already in a session")
	}

	cs.sessionId = sessionId
	return nil
}
