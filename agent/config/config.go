package config

import (
	"github.com/mosteligible/mcp-codemode/agent/constants"
)

type Config struct {
	DockerApiVersion string
	DockerImageName  string
	WorkerPort       string
	MinActive        int
}

func NewConfig() *Config {
	return &Config{
		DockerApiVersion: "1.40",
		DockerImageName:  constants.DefaultDockerImageName,
		WorkerPort:       constants.DefaultWorkerPort,
		MinActive:        constants.DefaultMinActive,
	}
}
