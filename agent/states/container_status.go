package states

const DefaultIdleContainerCleanupInterval = 300 // in seconds

type ContainerId string

type ContainerStatus struct {
	id         ContainerId
	lastExecAt int
	sessionId  string
}
