package handlers

import (
	"log/slog"
	"net/http"

	"github.com/mosteligible/mcp-codemode/coderunner/core/common"
	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
)

func getHeadersForEndpoint(target types.ProxyTarget) map[string]string {
	if target.Base == "github" {
		return map[string]string{
			"Authorization": "token " + target.Token,
		}
	} else {
		return map[string]string{
			"Authorization": "Bearer " + target.Token,
		}
	}
}

func RunProxyRequest(target types.ProxyTarget, client *http.Client) (map[string]interface{}, error) {
	headers := getHeadersForEndpoint(target)

	response, err := common.SendRequest(
		client,
		target.Url,
		headers,
		target.Method,
		nil,
	)

	if err != nil {
		slog.Error("failed sending request " + err.Error())
		return nil, err
	}
	defer response.Body.Close()

	return map[string]interface{}{
		"message": "Proxy request successful",
	}, nil
}
