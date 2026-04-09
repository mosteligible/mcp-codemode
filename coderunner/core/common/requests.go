package common

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strconv"
)

func SendRequest(
	ctx context.Context,
	client *http.Client,
	url string,
	headers map[string]string,
	method string,
	postBody map[string]string,
	correlationID string,
) (*http.Response, error) {
	var req *http.Request
	var response *http.Response
	var err error
	switch method {
	case http.MethodGet:
		req, err = http.NewRequestWithContext(ctx, method, url, nil)
	case http.MethodPost:
		var pb []byte
		if postBody != nil {
			pb, err = json.Marshal(postBody)
			req, err = http.NewRequestWithContext(ctx, method, url, bytes.NewBuffer(pb))
		} else {
			req, err = http.NewRequestWithContext(ctx, method, url, nil)
		}
	default:
		return nil, errors.New("Unsupported HTTP method")
	}
	if err != nil {
		slog.Error("error building request: " + err.Error() + " correlation_id: " + correlationID)
		return nil, err
	}

	slog.Info("starting request to: " + url + " correlation_id: " + correlationID)
	// for k, v := range headers {
	// 	req.Header.Set(k, v)
	// }
	response, err = client.Do(req)
	if err != nil {
		slog.Error("error sending request: " + err.Error() + " correlation_id: " + correlationID)
		return nil, err
	}
	if response.StatusCode > 399 {
		slog.Error(
			"API: <" + url + "> responded with status code: <" + strconv.Itoa(response.StatusCode) + "> correlation_id: " + correlationID,
		)
		return nil, errors.New("API responded with error status")
	}
	return response, nil
}
