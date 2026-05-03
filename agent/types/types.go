package types

type ContainerId string
type SessionId string

type HostResourceUsage struct {
	CPUPercent    float64
	MemoryPercent float64
}

type CPUStats struct {
	Idle  uint64
	Total uint64
}

type ExecuteResult struct {
	ExitCode int
	Stdout   string
	Stderr   string
}
