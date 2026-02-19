package states

import (
	"math/rand"
	"sync"
)

type ContainerState struct {
	Ids            []string
	readWriteMutex *sync.RWMutex
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

func (s *ContainerState) SetAvailableContainers() {

}
