package common

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"

	"github.com/mosteligible/mcp-codemode/agent-proto/pb"
	"github.com/mosteligible/mcp-codemode/coderunner/constants"
	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
	workerclient "github.com/mosteligible/mcp-codemode/coderunner/core/worker_client"
)

func SanitizeMessage(message string, remoteHosts []string) string {
	// remove any mention of remote host ips or ssh errors from message
	for _, host := range remoteHosts {
		message = strings.ReplaceAll(message, host, "remote_host")
	}
	return message
}

func GetTarget(r *http.Request, corrID string) (types.ProxyTarget, error) {
	path := r.PathValue("path")
	// path follows format: /github|graph/{endpoint} - endpoint is follow-through path
	// to be appended to base url of target API, for example: /github/repos/octocat/hello-world
	method := r.Method
	slog.Info("path: "+path+" - "+method, "correlation_id", corrID)
	if path[0] == '/' {
		path = path[1:]
	}
	parts := strings.Split(path, "/")
	var postBody map[string]interface{}
	var target types.ProxyTarget
	if method == http.MethodPost {
		err := json.NewDecoder(r.Body).Decode(&postBody)
		if err != nil {
			return types.ProxyTarget{}, errors.New("invalid post body - correlation_id: " + corrID)
		}
		target.PostBody = postBody
	}
	switch parts[0] {
	case constants.GITHUB_BASE:
		target.Base = constants.GITHUB_BASE
		target.Method = method
		target.Url = constants.GITHUB_BASE_URL + "/" + strings.Join(parts[1:], "/")
		return target, nil
	case constants.MICROSOFT_GRAPH_BASE:
		target.Base = constants.MICROSOFT_GRAPH_BASE
		target.Method = method
		target.Url = constants.MICROSOFT_GRAPH_BASE_URL + "/" + strings.Join(parts[1:], "/")
		return target, nil
	default:
		return types.ProxyTarget{}, errors.New("unknown path - correlation_id: " + corrID)
	}
}

func ExecuteCommand(ctx context.Context, connection *workerclient.WorkerClient, instruction, language string) types.CommandOutput {
	output := types.CommandOutput{}
	// execute the command and capture the output and error
	instruction = strings.TrimSpace(instruction)
	if instruction == "" {
		output.ErrorMessage = "No command provided"
		return output
	}

	result, err := connection.Client.ExecuteCode(
		ctx, &pb.ExecuteCodeRequest{
			Instruction: instruction,
			Language:    language,
		},
	)
	if err != nil {
		output.ErrorMessage = err.Error()
		return output
	}
	output.Output = result.Output

	return output
}

func GetErrorResponseMessage(msg string) map[string]string {
	return map[string]string{"message": msg}
}
