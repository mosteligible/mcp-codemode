package common

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/moby/moby/client"
	"github.com/mosteligible/mcp-codemode/agent/constants"
	"github.com/mosteligible/mcp-codemode/agent/types"
)

const cpuUsageSampleInterval = 100 * time.Millisecond

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

func GetHostResourceUsage() (types.HostResourceUsage, error) {
	firstCPUStats, err := readCPUStats()
	if err != nil {
		return types.HostResourceUsage{}, err
	}

	time.Sleep(cpuUsageSampleInterval)

	secondCPUStats, err := readCPUStats()
	if err != nil {
		return types.HostResourceUsage{}, err
	}

	memoryPercent, err := readMemoryUsagePercent()
	if err != nil {
		return types.HostResourceUsage{}, err
	}

	return types.HostResourceUsage{
		CPUPercent:    calculateCPUPercent(firstCPUStats, secondCPUStats),
		MemoryPercent: memoryPercent,
	}, nil
}

func readCPUStats() (types.CPUStats, error) {
	data, err := os.ReadFile("/proc/stat")
	if err != nil {
		return types.CPUStats{}, fmt.Errorf("read cpu stats: %w", err)
	}
	return parseCPUStats(string(data))
}

func parseCPUStats(data string) (types.CPUStats, error) {
	for _, line := range strings.Split(data, "\n") {
		fields := strings.Fields(line)
		if len(fields) == 0 || fields[0] != "cpu" {
			continue
		}
		if len(fields) < 5 {
			return types.CPUStats{}, fmt.Errorf("invalid cpu stats format")
		}

		values := make([]uint64, 0, len(fields)-1)
		for _, field := range fields[1:] {
			value, err := strconv.ParseUint(field, 10, 64)
			if err != nil {
				return types.CPUStats{}, fmt.Errorf("parse cpu stat value %q: %w", field, err)
			}
			values = append(values, value)
		}

		var total uint64
		for i, value := range values {
			// guest and guest_nice are already included in user and nice.
			if i > 7 {
				break
			}
			total += value
		}

		idle := values[3]
		if len(values) > 4 {
			idle += values[4]
		}

		return types.CPUStats{
			Idle:  idle,
			Total: total,
		}, nil
	}

	return types.CPUStats{}, fmt.Errorf("cpu stats not found")
}

func calculateCPUPercent(first, second types.CPUStats) float64 {
	if second.Total <= first.Total || second.Idle < first.Idle {
		return 0
	}

	totalDelta := second.Total - first.Total
	if totalDelta == 0 {
		return 0
	}

	idleDelta := second.Idle - first.Idle
	if idleDelta > totalDelta {
		return 0
	}

	return float64(totalDelta-idleDelta) / float64(totalDelta) * 100
}

func readMemoryUsagePercent() (float64, error) {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0, fmt.Errorf("read memory stats: %w", err)
	}
	return parseMemoryUsagePercent(string(data))
}

func parseMemoryUsagePercent(data string) (float64, error) {
	var totalMemory uint64
	var availableMemory uint64
	var totalFound bool
	var availableFound bool

	for _, line := range strings.Split(data, "\n") {
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}

		switch strings.TrimSuffix(fields[0], ":") {
		case "MemTotal", "MemAvailable":
			value, err := strconv.ParseUint(fields[1], 10, 64)
			if err != nil {
				return 0, fmt.Errorf("parse memory stat value %q: %w", fields[1], err)
			}

			switch strings.TrimSuffix(fields[0], ":") {
			case "MemTotal":
				totalMemory = value
				totalFound = true
			case "MemAvailable":
				availableMemory = value
				availableFound = true
			}
		}
	}

	if !totalFound || totalMemory == 0 {
		return 0, fmt.Errorf("memory total not found")
	}
	if !availableFound {
		return 0, fmt.Errorf("available memory not found")
	}
	if availableMemory > totalMemory {
		return 0, fmt.Errorf("available memory exceeds total memory")
	}

	return float64(totalMemory-availableMemory) / float64(totalMemory) * 100, nil
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
