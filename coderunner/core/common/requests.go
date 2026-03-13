package common

import (
	"bytes"
	"encoding/json"
	"errors"
	"log"
	"net/http"
)

func SendRequest(
	client *http.Client,
	url string,
	headers map[string]string,
	method string,
	postBody *map[string]string,
) (*http.Response, error) {
	var req *http.Request
	var response *http.Response
	var err error
	switch method {
	case http.MethodGet:
		req, err = http.NewRequest(method, url, nil)
	case http.MethodPost:
		var pb []byte
		pb, err = json.Marshal(postBody)
		req, err = http.NewRequest(method, url, bytes.NewBuffer(pb))
	default:
		return nil, errors.New("Unsupported HTTP method")
	}
	if err != nil {
		log.Printf("error building request: %s\n", err.Error())
		return nil, err
	}

	log.Printf("starting request to: %s", url)
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	response, err = client.Do(req)
	if err != nil {
		log.Printf("error sending request: %s\n", err.Error())
		return nil, err
	}
	if response.StatusCode > 399 {
		log.Printf("API: <%s> respoded with status code: <%d>", url, response.StatusCode)
		return nil, errors.New("API responded with error status")
	}
	return response, nil
}
