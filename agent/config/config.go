package config

import (
	"log"

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
	otelHeader := common.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_HEADERS", "")
	if otelHeader == "" {
		log.Fatalf("OTEL_EXPORTER_OTLP_HEADERS not set in environment")
	}
	otelEndpoint := common.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT", "")
	if otelEndpoint == "" {
		log.Fatalf("OTEL_EXPORTER_OTLP_ENDPOINT not set in environment")
	}

	return &Config{
		DockerApiVersion:             common.GetEnvironmentVariable("DOCKER_API_VERSION", constants.DefaultDockerApiVersion),
		DockerImageName:              common.GetEnvironmentVariable("DOCKER_IMAGE_NAME", constants.DefaultDockerImageName),
		WorkerPort:                   common.GetEnvironmentVariable("WORKER_PORT", constants.DefaultWorkerPort),
		MinActive:                    common.GetEnvironmentVariable("MIN_ACTIVE", constants.DefaultMinActive),
		ActiveContainerCheckInterval: common.GetEnvironmentVariable("ACTIVE_CONTAINER_CHECK_INTERVAL", constants.DefaultContainerCheckInterval),
	}
}
