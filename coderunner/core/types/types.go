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

type ProxyTarget struct {
	Url      string
	Token    string
	Base     string
	Method   string
	PostBody map[string]interface{}
}
