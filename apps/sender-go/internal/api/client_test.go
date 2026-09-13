package api

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestProcessSendJobSendsTheContractHeadersAndReadsTheOutcome(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/internal/send-jobs/job-1/process" {
			t.Errorf("request = %s %s", r.Method, r.URL.Path)
		}
		if r.Header.Get(WorkspaceHeader) != "workspace-1" || r.Header.Get(InternalTokenHeader) != "token" {
			t.Errorf("headers = %v", r.Header)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"job_id":"job-1","outcome":"sent"}`))
	}))
	defer server.Close()

	result, err := NewClient(server.URL+"/", "token", server.Client()).ProcessSendJob(context.Background(), "workspace-1", "job-1")
	if err != nil {
		t.Fatalf("ProcessSendJob: %v", err)
	}
	if result != (ProcessResult{JobID: "job-1", Outcome: "sent"}) {
		t.Errorf("result = %+v", result)
	}
}

func TestProcessSendJobReturnsTheStatusOnFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusConflict)
		_, _ = w.Write([]byte(`{"detail":"Send job is not claimed"}`))
	}))
	defer server.Close()

	_, err := NewClient(server.URL, "token", server.Client()).ProcessSendJob(context.Background(), "workspace-1", "job-1")
	var statusErr *StatusError
	if !errors.As(err, &statusErr) || statusErr.StatusCode != http.StatusConflict {
		t.Fatalf("error = %v, want a 409 StatusError", err)
	}
}
