package types

import "net/http"

type CodeRunnerRequest struct {
	Code     string `json:"code"`
	Language string `json:"language"`
}

type CommandOutput struct {
	Output       string `json:"output"`
	ErrorMessage string `json:"error,omitempty"`
	Err          error  `json:"-"`
}

type CommResponse struct {
	Response *http.Response
	Err      error
}

type ProxyTarget struct {
	Url    string
	Token  string
	Base   string
	Method string
}
