package types

type CodeRunnerRequest struct {
	Code     string `json:"code"`
	Language string `json:"language"`
}

type CommandOutput struct {
	Output string `json:"output"`
	Error  string `json:"error,omitempty"`
}
