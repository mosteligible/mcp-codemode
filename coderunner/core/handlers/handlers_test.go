package handlers

import (
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
)

func Test_getHeadersForEndpoint(t *testing.T) {
	tests := []struct {
		name string // description of this test case
		// Named input parameters for target function.
		target types.ProxyTarget
		want   map[string]string
	}{
		{
			name: "github uses token auth header",
			target: types.ProxyTarget{
				Base:  "github",
				Token: "ghp_123",
			},
			want: map[string]string{
				"Authorization": "token ghp_123",
			},
		},
		{
			name: "non github uses bearer auth header",
			target: types.ProxyTarget{
				Base:  "microsoft_graph",
				Token: "graph-token",
			},
			want: map[string]string{
				"Authorization": "Bearer graph-token",
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := getHeadersForEndpoint(tt.target)
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("getHeadersForEndpoint() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestRunProxyRequest(t *testing.T) {
	tests := []struct {
		name    string // description of this test case
		setup   func(t *testing.T) (types.ProxyTarget, *http.Client)
		want    map[string]interface{}
		wantErr bool
	}{
		{
			name: "successful github proxy request",
			setup: func(t *testing.T) (types.ProxyTarget, *http.Client) {
				t.Helper()

				server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					if r.Method != http.MethodGet {
						t.Errorf("expected method %q, got %q", http.MethodGet, r.Method)
					}
					if got := r.Header.Get("Authorization"); got != "token ghp_123" {
						t.Errorf("expected Authorization header %q, got %q", "token ghp_123", got)
					}
					w.WriteHeader(http.StatusOK)
				}))
				t.Cleanup(server.Close)

				return types.ProxyTarget{
					Url:    server.URL,
					Token:  "ghp_123",
					Base:   "github",
					Method: http.MethodGet,
				}, server.Client()
			},
			want: map[string]interface{}{
				"message": "Proxy request successful",
			},
			wantErr: false,
		},
		{
			name: "returns error when upstream responds with error status",
			setup: func(t *testing.T) (types.ProxyTarget, *http.Client) {
				t.Helper()

				server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					if got := r.Header.Get("Authorization"); got != "Bearer graph-token" {
						t.Errorf("expected Authorization header %q, got %q", "Bearer graph-token", got)
					}
					w.WriteHeader(http.StatusBadGateway)
				}))
				t.Cleanup(server.Close)

				return types.ProxyTarget{
					Url:    server.URL,
					Token:  "graph-token",
					Base:   "microsoft_graph",
					Method: http.MethodGet,
				}, server.Client()
			},
			want:    nil,
			wantErr: true,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			target, client := tt.setup(t)
			got, gotErr := RunProxyRequest(target, client, "test-correlation-id")
			if gotErr != nil {
				if !tt.wantErr {
					t.Errorf("RunProxyRequest() failed: %v", gotErr)
				}
				return
			}
			if tt.wantErr {
				t.Fatal("RunProxyRequest() succeeded unexpectedly")
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("RunProxyRequest() = %v, want %v", got, tt.want)
			}
		})
	}
}
