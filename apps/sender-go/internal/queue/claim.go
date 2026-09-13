package queue

import (
	"context"
	"fmt"
	"regexp"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgtype"
)

const Lease = 5 * time.Minute

const ClaimStatement = `UPDATE campaign__send_jobs
SET status = 'running',
    locked_at = :moment,
    locked_by = :worker_id,
    attempts = attempts + 1,
    updated_at = :moment
WHERE id IN (
    SELECT id FROM campaign__send_jobs
    WHERE workspace_id = :workspace_id
      AND (
        (status = 'pending' AND scheduled_at <= :moment)
        OR (status = 'running' AND locked_at < :lease_expired_before)
      )
    ORDER BY scheduled_at
    LIMIT :limit
    FOR UPDATE SKIP LOCKED
)
RETURNING id, workspace_id, mailbox_id, lead_id, payload, attempts, scheduled_at
`

var namedParameter = regexp.MustCompile(`(^|[^:]):([a-z_]+)`)

var pgxClaimStatement = namedParameter.ReplaceAllString(ClaimStatement, "${1}@${2}")

type Querier interface {
	Exec(ctx context.Context, sql string, arguments ...any) (pgconn.CommandTag, error)
	Query(ctx context.Context, sql string, arguments ...any) (pgx.Rows, error)
}

type ClaimRequest struct {
	WorkspaceID string
	WorkerID    string
	Limit       int
	Moment      time.Time
}

func Claim(ctx context.Context, tx Querier, request ClaimRequest) ([]Job, error) {
	var workspaceID pgtype.UUID
	if err := workspaceID.Scan(request.WorkspaceID); err != nil {
		return nil, fmt.Errorf("workspace id %q: %w", request.WorkspaceID, err)
	}
	if _, err := tx.Exec(ctx, "SELECT set_config('app.workspace_id', $1, true)", request.WorkspaceID); err != nil {
		return nil, fmt.Errorf("set workspace for row-level security: %w", err)
	}

	rows, err := tx.Query(ctx, pgxClaimStatement, pgx.NamedArgs{
		"moment":               request.Moment,
		"worker_id":            request.WorkerID,
		"workspace_id":         workspaceID,
		"lease_expired_before": request.Moment.Add(-Lease),
		"limit":                request.Limit,
	})
	if err != nil {
		return nil, fmt.Errorf("claim send jobs: %w", err)
	}
	defer rows.Close()

	var jobs []Job
	for rows.Next() {
		var id, workspace, mailbox, lead [16]byte
		var payload []byte
		var attempts int32
		var scheduledAt time.Time
		if err := rows.Scan(&id, &workspace, &mailbox, &lead, &payload, &attempts, &scheduledAt); err != nil {
			return nil, fmt.Errorf("read claimed send job: %w", err)
		}
		decoded, payloadErr := DecodePayload(payload)
		jobs = append(jobs, Job{
			ID:           formatUUID(id),
			WorkspaceID:  formatUUID(workspace),
			MailboxID:    formatUUID(mailbox),
			LeadID:       formatUUID(lead),
			Payload:      decoded,
			PayloadError: payloadErr,
			Attempts:     int(attempts),
			ScheduledAt:  scheduledAt,
		})
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("claim send jobs: %w", err)
	}
	return jobs, nil
}

func formatUUID(value [16]byte) string {
	return fmt.Sprintf("%x-%x-%x-%x-%x", value[0:4], value[4:6], value[6:8], value[8:10], value[10:16])
}
