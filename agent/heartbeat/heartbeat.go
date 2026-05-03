package heartbeat

import (
	"context"
	"encoding/json"
	"log/slog"
	"time"

	"github.com/mosteligible/mcp-codemode/agent/config"
	"github.com/mosteligible/mcp-codemode/agent/core/common"
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

func (b *Beat) MarshalBinary() ([]byte, error) {
	return json.Marshal(b)
}

func (b *Beat) UnmarshalBinary(data []byte) error {
	return json.Unmarshal(data, b)
}

func (wc *WorkerCapacity) MarshalBinary() ([]byte, error) {
	return json.Marshal(wc)
}

func (wc *WorkerCapacity) UnmarshalBinary(data []byte) error {
	return json.Unmarshal(data, wc)
}

func NewBeat(appConfig *config.Config, containerState *states.ContainerState) *Beat {
	return &Beat{
		WorkerId:       appConfig.WorkerPort,
		interval:       appConfig.HeartBeatInterval,
		containerState: containerState,
	}
}

func (b *Beat) Start(redisClient *redis.Client, shutdownSignal chan struct{}) {
	ticker := time.NewTicker(time.Duration(b.interval) * time.Second)
	defer ticker.Stop()

	capacityKey := b.WorkerId + ":capacity"
	for {
		select {
		case <-ticker.C:
			workerCapacity, err := GetWorkerCapacity(redisClient, b.WorkerId, b.containerState)
			if err == nil {
				err := redisClient.Set(
					context.Background(), capacityKey, workerCapacity, time.Duration(b.interval)*time.Second,
				).Err()
				if err != nil {
					slog.Error("error setting worker capacity", "error", err.Error())
				}
			} else {
				slog.Error("error getting worker capacity", "error", err.Error())
			}
			b.LastUpdated = time.Now()
			err = redisClient.Set(context.Background(), b.WorkerId, b, time.Duration(b.interval)*time.Second).Err()
			if err != nil {
				slog.Error("error setting worker status", "error", err.Error())
			}
		case <-shutdownSignal:
			return
		}
	}
}

func GetWorkerCapacity(redisClient *redis.Client, workerId string, containerState *states.ContainerState) (*WorkerCapacity, error) {
	// returns the current cpu and memory usage of the worker, as well as the number of available slots for new tasks
	hostResourceUsage, err := common.GetHostResourceUsage()
	if err != nil {
		return nil, err
	}

	return &WorkerCapacity{
		WorkerId:      workerId,
		State:         WorkerStateAvailable,
		CpuPercent:    hostResourceUsage.CPUPercent,
		MemoryPercent: hostResourceUsage.MemoryPercent,
		LastUpdated:   time.Now(),
		MaxSlots:      containerState.GetMaxSlots(),
	}, nil
}
