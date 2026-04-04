package interceptors

import (
	"context"
	"log/slog"
	"time"

	"go.opentelemetry.io/otel/trace"
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
	spanContext := trace.SpanContextFromContext(ctx)
	traceID := ""
	spanID := ""
	if spanContext.IsValid() {
		traceID = spanContext.TraceID().String()
		spanID = spanContext.SpanID().String()
	}
	if !(info.FullMethod == "/agent.server.") {
		logFn(
			"grpc-request",
			"method", info.FullMethod,
			"code", status.Code(err),
			"duration_ms", duration,
			"trace_id", traceID,
			"span_id", spanID,
		)
	}
	return resp, err
}
