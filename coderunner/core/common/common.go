package common

import (
	"errors"
	"os/exec"
	"strings"

	"github.com/mosteligible/mcp-codemode/coderunner/constants"
	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
)

func SanitizeMessage(message string, remoteHosts []string) string {
	// remove any mention of remote host ips or ssh errors from message
	for _, host := range remoteHosts {
		message = strings.ReplaceAll(message, host, "remote_host")
	}
	return message
}

func GetUrlFromProxyPath(path, method string) (types.ProxyTarget, error) {
	if path[0] != '/' {
		return types.ProxyTarget{}, errors.New("invalid path")
	}
	parts := strings.Split(path[1:], "/")
	switch parts[0] {
	case constants.GITHUB_BASE:
		return types.ProxyTarget{
			Base:   constants.GITHUB_BASE,
			Url:    constants.GITHUB_BASE_URL,
			Method: method,
		}, nil
	case constants.MICROSOFT_GRAPH_BASE:
		return types.ProxyTarget{
			Base:   constants.MICROSOFT_GRAPH_BASE,
			Url:    constants.MICROSOFT_GRAPH_BASE_URL,
			Method: method,
		}, nil
	default:
		return types.ProxyTarget{}, errors.New("unknown path")
	}
}

func ExecuteCommand(appUserName, remoteHost, instruction string) types.CommandOutput {
	output := types.CommandOutput{}
	// execute the command and capture the output and error
	instruction = strings.TrimSpace(instruction)
	if instruction == "" {
		output.ErrorMessage = "No command provided"
		return output
	}

	instruction = appUserName + "@" + remoteHost + " '" + instruction + "'"

	cmd := exec.Command(
		"ssh",
		"-t",
		instruction,
	)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		output.ErrorMessage = err.Error()
		output.Err = err
	}
	output.Output = string(outputBytes)
	return output
}
