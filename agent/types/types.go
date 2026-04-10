package types

type ContainerId string
type SessionId string

type ExecuteResult struct {
	ExitCode int
	Stdout   string
	Stderr   string
}
