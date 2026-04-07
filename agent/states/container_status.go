package states

import (
	"fmt"
	"time"

	"github.com/mosteligible/mcp-codemode/agent/types"
)

const DefaultIdleContainerCleanupInterval = 300 // in seconds

type ContainerStatus struct {
	id         types.ContainerId
	lastExecAt time.Time
	startedAt  time.Time
	sessionId  types.SessionId
}

func NewContainerStatus(id types.ContainerId, sessionId string) ContainerStatus {
	return ContainerStatus{
		id:        types.ContainerId(id),
		sessionId: types.SessionId(sessionId),
		startedAt: time.Now(),
	}
}

func (cs *ContainerStatus) IsAvailable() bool {
	return cs.sessionId == ""
}

func (cs *ContainerStatus) AddSession(sessionId string) error {
	if cs.sessionId != "" {
		return fmt.Errorf("container is already in a session")
	}

	cs.sessionId = types.SessionId(sessionId)
	return nil
}
