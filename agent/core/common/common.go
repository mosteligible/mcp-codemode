package common

import (
	"context"
	"fmt"
	"log/slog"
	"os"

	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent/constants"
)

func GetEnvironmentVariable[T comparable](envVarName string, defaultValue T) T {
	value, exists := os.LookupEnv(envVarName)
	if !exists {
		return defaultValue
	}

	var result T
	switch any(result).(type) {
	case string:
		result = any(value).(T)
	case int:
		// Convert string to int
		var intValue int
		_, err := fmt.Sscanf(value, "%d", &intValue)
		if err != nil {
			return defaultValue
		}
		result = any(intValue).(T)
	default:
		slog.Warn("could not convert var: " + envVarName + " to type, returning default value - " + fmt.Sprintf("%v", defaultValue))
		return defaultValue
	}
	return result
}

func GetActiveContainerIds(containerClient *client.Client) ([]string, error) {
	containers, err := containerClient.ContainerList(context.Background(), client.ContainerListOptions{})
	if err != nil {
		return nil, err
	}

	ids := make([]string, len(containers.Items))
	for i, container := range containers.Items {
		ids[i] = container.ID
	}
	return ids, nil
}

func ValidateProgrammingLanguage(language string) error {
	switch language {
	case constants.ProgrammingLanguagePython, constants.ProgrammingLanguageBash:
		return nil
	default:
		return fmt.Errorf("unsupported programming language: %s", language)
	}
}
