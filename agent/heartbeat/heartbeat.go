package heartbeat

import (
	"context"
	"time"

	"github.com/mosteligible/mcp-codemode/agent/config"
	"github.com/mosteligible/mcp-codemode/agent/states"
	"github.com/redis/go-redis/v9"
)

type WorkerState string

const (
	WorkerStateAvailable   WorkerState = "available"
	WorkerStateUnavaialble WorkerState = "unavailable"
)

type Beat struct {
	WorkerId       string    `json:"worker_id"`
	LastUpdated    time.Time `json:"last_updated"`
	interval       int
	containerState *states.ContainerState
}

type WorkerCapacity struct {
	WorkerId       string      `json:"worker_id"`
	State          WorkerState `json:"state"`
	CpuPercent     float64     `json:"cpu_percent"`
	MemoryPercent  float64     `json:"memory_percent"`
	LastUpdated    time.Time   `json:"last_updated"`
	MaxSlots       int         `json:"max_slots"`
	AvailableSlots int         `json:"available_slots"`
}

func NewBeat(appConfig config.Config, containerState *states.ContainerState) *Beat {
	return &Beat{
		WorkerId:       appConfig.WorkerPort,
		interval:       appConfig.ActiveContainerCheckInterval,
		containerState: containerState,
	}
}

func (b *Beat) Start(redisClient *redis.Client, shutdownSignal chan struct{}) {
	ticker := time.NewTicker(time.Duration(b.interval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			err := redisClient.Set(context.Background(), b.WorkerId, "alive", time.Duration(b.interval)*time.Second).Err()
			if err != nil {
			}
		case <-shutdownSignal:
			return
		}
	}
}

func GetWorkerCapacity(redisClient *redis.Client, workerId string, containerState *states.ContainerState) (*WorkerCapacity, error) {
	// returns the current cpu and memory usage of the worker, as well as the number of available slots for new tasks
	return &WorkerCapacity{
		WorkerId: workerId,
		State:    WorkerStateAvailable,
		// CpuPercent:    getCpuUsage(),
		// MemoryPercent: getMemoryUsage(),
		LastUpdated: time.Now(),
		MaxSlots:    containerState.GetMaxSlots(),
	}, nil
}
