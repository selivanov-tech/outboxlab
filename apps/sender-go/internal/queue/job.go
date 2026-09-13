package queue

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"time"
)

const SupportedJobVersion = 1

var ErrUnsupportedJobVersion = errors.New("unsupported send job version")

var requiredPayloadFields = []string{
	"job_version",
	"campaign_id",
	"lead_id",
	"step_id",
	"step_position",
	"to_email",
	"subject",
	"body",
}

type SendJobV1 struct {
	JobVersion   int    `json:"job_version"`
	CampaignID   string `json:"campaign_id"`
	LeadID       string `json:"lead_id"`
	StepID       string `json:"step_id"`
	StepPosition int    `json:"step_position"`
	ToEmail      string `json:"to_email"`
	Subject      string `json:"subject"`
	Body         string `json:"body"`
}

type Job struct {
	ID           string
	WorkspaceID  string
	MailboxID    string
	LeadID       string
	Payload      SendJobV1
	PayloadError error
	Attempts     int
	ScheduledAt  time.Time
}

func DecodePayload(raw []byte) (SendJobV1, error) {
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return SendJobV1{}, fmt.Errorf("decode send job payload: %w", err)
	}
	for _, name := range requiredPayloadFields {
		if _, present := fields[name]; !present {
			return SendJobV1{}, fmt.Errorf("send job payload is missing %q", name)
		}
	}

	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	var payload SendJobV1
	if err := decoder.Decode(&payload); err != nil {
		return SendJobV1{}, fmt.Errorf("decode send job payload: %w", err)
	}
	if payload.JobVersion != SupportedJobVersion {
		return SendJobV1{}, fmt.Errorf("%w: %d", ErrUnsupportedJobVersion, payload.JobVersion)
	}
	if payload.StepPosition < 1 {
		return SendJobV1{}, fmt.Errorf("send job step_position must be at least 1, got %d", payload.StepPosition)
	}
	return payload, nil
}
