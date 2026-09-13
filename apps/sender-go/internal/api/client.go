package api

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

const (
	WorkspaceHeader     = "X-Workspace-Id"
	InternalTokenHeader = "X-Internal-Token"
	maxResponseBytes    = 64 << 10
)

type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

type ProcessResult struct {
	JobID   string `json:"job_id"`
	Outcome string `json:"outcome"`
}

type StatusError struct {
	StatusCode int
	Body       string
}

func (e *StatusError) Error() string {
	return fmt.Sprintf("internal API answered %d: %s", e.StatusCode, e.Body)
}

func NewClient(baseURL, token string, httpClient *http.Client) *Client {
	return &Client{baseURL: strings.TrimRight(baseURL, "/"), token: token, http: httpClient}
}

func (c *Client) ProcessSendJob(ctx context.Context, workspaceID, jobID string) (ProcessResult, error) {
	endpoint := fmt.Sprintf("%s/internal/send-jobs/%s/process", c.baseURL, url.PathEscape(jobID))
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, nil)
	if err != nil {
		return ProcessResult{}, fmt.Errorf("build request: %w", err)
	}
	request.Header.Set(WorkspaceHeader, workspaceID)
	request.Header.Set(InternalTokenHeader, c.token)
	request.Header.Set("Accept", "application/json")

	response, err := c.http.Do(request)
	if err != nil {
		return ProcessResult{}, fmt.Errorf("call internal API: %w", err)
	}
	defer response.Body.Close()

	body, err := io.ReadAll(io.LimitReader(response.Body, maxResponseBytes))
	if err != nil {
		return ProcessResult{}, fmt.Errorf("read internal API response: %w", err)
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return ProcessResult{}, &StatusError{StatusCode: response.StatusCode, Body: strings.TrimSpace(string(body))}
	}
	var result ProcessResult
	if err := json.Unmarshal(body, &result); err != nil {
		return ProcessResult{}, fmt.Errorf("decode internal API response: %w", err)
	}
	return result, nil
}
