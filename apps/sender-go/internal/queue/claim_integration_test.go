package queue

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
)

const seedTwoJobs = `
WITH workspace AS (
    INSERT INTO identity__workspaces (id, name, created_at)
    VALUES (gen_random_uuid(), 'go-claim-test', now())
    RETURNING id
), mailbox AS (
    INSERT INTO mailbox__mailboxes (id, workspace_id, email_address, last_sync_cursor, daily_send_cap, created_at)
    SELECT gen_random_uuid(), id, 'ops@example.com', NULL, 20, now() FROM workspace
    RETURNING id, workspace_id
), campaign AS (
    INSERT INTO campaign__campaigns (id, workspace_id, mailbox_id, name, status, created_at)
    SELECT gen_random_uuid(), workspace_id, id, 'Go claim test', 'active', now() FROM mailbox
    RETURNING id, workspace_id, mailbox_id
), step AS (
    INSERT INTO campaign__steps (id, workspace_id, campaign_id, position, subject, body, delay_seconds, created_at)
    SELECT gen_random_uuid(), workspace_id, id, 1, 'Hello', 'First touch', 0, now() FROM campaign
    RETURNING id, workspace_id, campaign_id
), lead AS (
    INSERT INTO campaign__leads (id, workspace_id, campaign_id, email, state, steps_sent, stop_reason, reply_intent, created_at, updated_at)
    SELECT gen_random_uuid(), workspace_id, campaign_id, 'lead@example.com', 'scheduled', 0, NULL, NULL, now(), now() FROM step
    RETURNING id, workspace_id, campaign_id
), jobs AS (
    INSERT INTO campaign__send_jobs (id, workspace_id, mailbox_id, lead_id, step_id, payload, scheduled_at, status, attempts, locked_at, locked_by, last_error, outbound_message_id, created_at, updated_at)
    SELECT gen_random_uuid(), lead.workspace_id, campaign.mailbox_id, lead.id, step.id,
        jsonb_build_object(
            'job_version', 1, 'campaign_id', campaign.id, 'lead_id', lead.id, 'step_id', step.id,
            'step_position', due.step_position, 'to_email', 'lead@example.com', 'subject', 'Hello', 'body', 'First touch'
        ),
        due.scheduled_at, 'pending', 0, NULL, NULL, NULL, NULL, now(), now()
    FROM lead, step, campaign,
        (VALUES (1, now() - interval '1 minute'), (2, now() + interval '1 hour')) AS due (step_position, scheduled_at)
    RETURNING id, workspace_id, scheduled_at
)
SELECT workspace_id::text, id::text FROM jobs WHERE scheduled_at < now()
`

func TestClaimIntegration(t *testing.T) {
	databaseURL := os.Getenv("TEST_DATABASE_URL")
	if databaseURL == "" {
		t.Skip("TEST_DATABASE_URL is not set")
	}
	ctx := context.Background()
	conn, err := pgx.Connect(ctx, databaseURL)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	defer conn.Close(ctx)
	tx, err := conn.Begin(ctx)
	if err != nil {
		t.Fatalf("begin: %v", err)
	}
	defer tx.Rollback(ctx)

	var workspaceID, dueJobID string
	if err := tx.QueryRow(ctx, seedTwoJobs).Scan(&workspaceID, &dueJobID); err != nil {
		t.Fatalf("seed: %v", err)
	}
	moment := time.Now().UTC()
	claim := func(at time.Time, workerID string) []Job {
		t.Helper()
		jobs, err := Claim(ctx, tx, ClaimRequest{WorkspaceID: workspaceID, WorkerID: workerID, Limit: 10, Moment: at})
		if err != nil {
			t.Fatalf("claim: %v", err)
		}
		return jobs
	}

	first := claim(moment, "go-test-1")
	if len(first) != 1 || first[0].ID != dueJobID {
		t.Fatalf("first claim = %+v, want only job %s", first, dueJobID)
	}
	job := first[0]
	if job.PayloadError != nil || job.Payload.StepPosition != 1 || job.Attempts != 1 || job.WorkspaceID != workspaceID {
		t.Fatalf("claimed job = %+v", job)
	}
	var status, lockedBy string
	if err := tx.QueryRow(ctx, "SELECT status, locked_by FROM campaign__send_jobs WHERE id::text = $1", dueJobID).Scan(&status, &lockedBy); err != nil {
		t.Fatalf("read job: %v", err)
	}
	if status != "running" || lockedBy != "go-test-1" {
		t.Fatalf("job row = %s / %s", status, lockedBy)
	}

	if again := claim(moment.Add(time.Minute), "go-test-2"); len(again) != 0 {
		t.Fatalf("claim inside the lease = %+v, want none", again)
	}
	reclaimed := claim(moment.Add(Lease+time.Second), "go-test-2")
	if len(reclaimed) != 1 || reclaimed[0].ID != dueJobID || reclaimed[0].Attempts != 2 {
		t.Fatalf("claim after the lease = %+v", reclaimed)
	}
}
