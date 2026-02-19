package middlewares

import (
	"log/slog"
	"net/http"
)

func LoggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		slog.Info("%s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
