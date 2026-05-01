package config

import (
	"github.com/mosteligible/mcp-codemode/agent/constants"
	"github.com/mosteligible/mcp-codemode/agent/core/common"
)

type Config struct {
	DockerApiVersion             string
	DockerImageName              string
	WorkerPort                   string
	MinActiveContainers          int
	MaxActiveContainers          int
	ActiveContainerCheckInterval int
	HeartBeatInterval            int

	RedisHost     string
	RedisPort     string
	RedisPassword string
	RedisDb       int
}

func NewConfig() *Config {

	return &Config{
		DockerApiVersion:             common.GetEnvironmentVariable("DOCKER_API_VERSION", constants.DefaultDockerApiVersion),
		DockerImageName:              common.GetEnvironmentVariable("DOCKER_IMAGE_NAME", constants.DefaultDockerImageName),
		WorkerPort:                   common.GetEnvironmentVariable("WORKER_PORT", constants.DefaultWorkerPort),
		MinActiveContainers:          common.GetEnvironmentVariable("MIN_ACTIVE_CONTAINERS", constants.DefaultMinActive),
		MaxActiveContainers:          common.GetEnvironmentVariable("MAX_ACTIVE_CONTAINERS", constants.DefaultMaxActive),
		ActiveContainerCheckInterval: common.GetEnvironmentVariable("ACTIVE_CONTAINER_CHECK_INTERVAL", constants.DefaultContainerCheckInterval),
		HeartBeatInterval:            common.GetEnvironmentVariable("HEART_BEAT_INTERVAL", constants.DefaultHeartBeatInterval),
		RedisHost:                    common.GetEnvironmentVariable("REDIS_HOST", "localhost"),
		RedisPort:                    common.GetEnvironmentVariable("REDIS_PORT", "6379"),
		RedisPassword:                common.GetEnvironmentVariable("REDIS_PASSWORD", ""),
		RedisDb:                      common.GetEnvironmentVariable("REDIS_DB", 0),
	}
}
