package states

import (
	"log/slog"
	"math/rand"
	"sync"
)

type ExecutorState struct {
	Ids            []string
	readWriteMutex *sync.RWMutex
}

func NewExecutorState() *ExecutorState {
	slog.Warn("no minimum number of containers set")
	cs := &ExecutorState{
		Ids:            []string{},
		readWriteMutex: &sync.RWMutex{},
	}

	return cs
}

func (s *ExecutorState) GetAContainer() string {
	s.readWriteMutex.RLock()
	defer s.readWriteMutex.RUnlock()
	if len(s.Ids) == 0 {
		return ""
	}
	index := rand.Intn(len(s.Ids))
	return s.Ids[index]
}
