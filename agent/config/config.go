package config

import (
	"github.com/mosteligible/mcp-codemode/agent/constants"
	"github.com/mosteligible/mcp-codemode/agent/core/common"
)

type Config struct {
	DockerApiVersion             string
	DockerImageName              string
	WorkerPort                   string
	MinActive                    int
	ActiveContainerCheckInterval int
}

func NewConfig() *Config {
	return &Config{
		DockerApiVersion:             common.GetEnvironmentVariable("DOCKER_API_VERSION", constants.DefaultDockerApiVersion),
		DockerImageName:              common.GetEnvironmentVariable("DOCKER_IMAGE_NAME", constants.DefaultDockerImageName),
		WorkerPort:                   common.GetEnvironmentVariable("WORKER_PORT", constants.DefaultWorkerPort),
		MinActive:                    common.GetEnvironmentVariable("MIN_ACTIVE", constants.DefaultMinActive),
		ActiveContainerCheckInterval: common.GetEnvironmentVariable("ACTIVE_CONTAINER_CHECK_INTERVAL", constants.DefaultContainerCheckInterval),
	}
}
