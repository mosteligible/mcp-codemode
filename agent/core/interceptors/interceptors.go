package interceptors

import (
	"context"
	"log/slog"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/status"
)

func UnaryInterceptorLogger(
	ctx context.Context,
	req any,
	info *grpc.UnaryServerInfo,
	handler grpc.UnaryHandler,
) (any, error) {
	logFn := slog.Info
	start := time.Now()
	resp, err := handler(ctx, req)
	duration := time.Since(start).Milliseconds()
	if err != nil {
		logFn = slog.Error
	}
	if !(info.FullMethod == "/agent.server.") {
		logFn(
			"grpc-request",
			"method", info.FullMethod,
			"code", status.Code(err),
			"duration_ms", duration,
		)
	}
	return resp, err
}
