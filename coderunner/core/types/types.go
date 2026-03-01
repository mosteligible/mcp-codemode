package types

type CodeRunnerRequest struct {
	Code     string `json:"code"`
	Language string `json:"language"`
}

type CommandOutput struct {
	Output       string `json:"output"`
	ErrorMessage string `json:"error,omitempty"`
	Err          error  `json:"-"`
}
