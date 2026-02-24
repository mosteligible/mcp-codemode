package common

import (
	"math/rand"
	"os/exec"
	"strings"

	"github.com/mosteligible/mcp-codemode/coderunner/config"
	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
)

func SanitizeMessage(message string) string {
	// remove any mention of remote host ips or ssh errors from message
	for _, host := range config.Conf.RemoteHosts {
		message = strings.ReplaceAll(message, host, "remote_host")
	}
	return message
}

func GetAnAvailableRemoteHost() string {
	return config.Conf.RemoteHosts[rand.Intn(len(config.Conf.RemoteHosts))]
}

func ExecuteCommand(instruction string) types.CommandOutput {
	output := types.CommandOutput{}
	// execute the command and capture the output and error
	instruction = strings.TrimSpace(instruction)
	if instruction == "" {
		output.Error = "No command provided"
		return output
	}

	remoteHost := GetAnAvailableRemoteHost()
	instruction = config.Conf.AppUserName + "@" + remoteHost + " '" + instruction + "'"

	cmd := exec.Command(
		"ssh",
		"-t",
		instruction,
	)
	outputBytes, err := cmd.CombinedOutput()
	if err != nil {
		output.Error = err.Error()
	}
	output.Output = string(outputBytes)
	return output
}
