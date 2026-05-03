package common

import (
	"testing"

	"github.com/mosteligible/mcp-codemode/agent/types"
)

func TestParseCPUStats(t *testing.T) {
	stats, err := parseCPUStats("cpu  100 50 25 800 20 5 0 0 40 60\ncpu0 10 0 0 90 0 0 0 0 0 0\n")
	if err != nil {
		t.Fatalf("parseCPUStats returned error: %v", err)
	}

	if stats.Idle != 820 {
		t.Fatalf("expected idle time 820, got %d", stats.Idle)
	}
	if stats.Total != 1000 {
		t.Fatalf("expected total time 1000, got %d", stats.Total)
	}
}

func TestCalculateCPUPercent(t *testing.T) {
	percent := calculateCPUPercent(
		types.CPUStats{Idle: 800, Total: 1000},
		types.CPUStats{Idle: 900, Total: 2000},
	)

	if percent != 90 {
		t.Fatalf("expected cpu percent 90, got %f", percent)
	}
}

func TestParseMemoryUsagePercent(t *testing.T) {
	percent, err := parseMemoryUsagePercent("MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 250 kB\n")
	if err != nil {
		t.Fatalf("parseMemoryUsagePercent returned error: %v", err)
	}

	if percent != 75 {
		t.Fatalf("expected memory percent 75, got %f", percent)
	}
}
