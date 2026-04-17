package types

type CodeRunnerRequest struct {
	Code      string `json:"code"`
	Language  string `json:"language"`
	SessionId string `json:"sessionId,omitempty"`
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
	PostBody map[string]any
}

func (t ProxyTarget) String() string {
	return "ProxyTarget{Base: " + t.Base + ", Url: " + t.Url + ", Method: " + t.Method + "}"
}
