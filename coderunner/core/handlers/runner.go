package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/mosteligible/mcp-codemode/coderunner/core/common"
	"github.com/mosteligible/mcp-codemode/coderunner/core/types"
)

func RunCode(w http.ResponseWriter, r *http.Request) {
	var codeRequest types.CodeRunnerRequest

	err := json.NewDecoder(r.Body).Decode(&codeRequest)
	if err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	output := common.ExecuteCommand(codeRequest.Code)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(output)
}
