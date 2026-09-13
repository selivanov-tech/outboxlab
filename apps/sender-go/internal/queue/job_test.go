package queue

import (
	"errors"
	"strings"
	"testing"
)

const validPayload = `{
  "job_version": 1,
  "campaign_id": "01a09a68-1b57-7696-968d-07159c21525e",
  "lead_id": "01a09a68-1b8a-76d4-abd3-d7ef6f42698b",
  "step_id": "01a09a68-1b8a-76d4-abd3-d7f0e1f780df",
  "step_position": 1,
  "to_email": "lead@example.com",
  "subject": "Hello",
  "body": "First touch"
}`

func TestDecodePayloadAcceptsTheV1Contract(t *testing.T) {
	payload, err := DecodePayload([]byte(validPayload))
	if err != nil {
		t.Fatalf("DecodePayload: %v", err)
	}
	if payload.StepPosition != 1 || payload.ToEmail != "lead@example.com" || payload.Subject != "Hello" {
		t.Errorf("payload = %+v", payload)
	}
}

func TestDecodePayloadRejectsAnotherVersion(t *testing.T) {
	raw := strings.Replace(validPayload, `"job_version": 1`, `"job_version": 2`, 1)
	if _, err := DecodePayload([]byte(raw)); !errors.Is(err, ErrUnsupportedJobVersion) {
		t.Fatalf("error = %v, want ErrUnsupportedJobVersion", err)
	}
}

func TestDecodePayloadRejectsAMissingField(t *testing.T) {
	raw := strings.Replace(validPayload, `"subject": "Hello",`, "", 1)
	_, err := DecodePayload([]byte(raw))
	if err == nil || !strings.Contains(err.Error(), `"subject"`) {
		t.Fatalf("error = %v, want a missing subject error", err)
	}
}

func TestDecodePayloadRejectsAnUnknownField(t *testing.T) {
	raw := strings.Replace(validPayload, `"body": "First touch"`, `"body": "First touch", "cc": "x@example.com"`, 1)
	if _, err := DecodePayload([]byte(raw)); err == nil {
		t.Fatal("expected an error for an unknown field")
	}
}
