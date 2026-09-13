UPDATE campaign__send_jobs
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
