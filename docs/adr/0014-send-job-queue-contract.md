# ADR 0014 — Send-job queue contract

**Status:** accepted (Step 3)

## Context

Campaign sends must be scheduled (a follow-up runs minutes to days after the first step), survive worker crashes, work with more than one worker, and be drainable by a second sender implementation (the Go sender in Step 5) without sharing code with the Python worker.

## Decision

- The table `campaign__send_jobs` is owned by the campaign context. Statuses: `pending`, `running`, `done`, `failed`, `cancelled`.
- The payload is frozen in [`contracts/jobs/send_job/v1.json`](../../contracts/jobs/send_job/v1.json) (`job_version: 1`).
- **Claim** is one statement:

  ```sql
  UPDATE campaign__send_jobs
  SET status = 'running', locked_at = :moment, locked_by = :worker_id,
      attempts = attempts + 1, updated_at = :moment
  WHERE id IN (
      SELECT id FROM campaign__send_jobs
      WHERE workspace_id = :workspace_id
        AND ((status = 'pending' AND scheduled_at <= :moment)
          OR (status = 'running' AND locked_at < :lease_expired_before))
      ORDER BY scheduled_at
      LIMIT :limit
      FOR UPDATE SKIP LOCKED
  )
  RETURNING id, workspace_id, mailbox_id, lead_id, payload, attempts, scheduled_at;
  ```

- **Lease of 5 minutes.** A `running` job whose lease expired is claimed again. No separate reaper process.
- The caller passes the clock (`:moment`), so application time drives the queue and tests are deterministic.
- The claim commits on its own. Each claimed job is then processed in its own transaction: sending guards (ADR 0015), send, advance the lead, schedule the next step at `sent_at + delay_seconds`, finish the job.
- **Outcomes:**

  | Result | Job | Lead |
  |---|---|---|
  | sent | `done`, `outbound_message_id` stored | `sent`, or `done` after the last step |
  | mailbox busy | `pending` again in a few seconds, attempt not counted | unchanged |
  | daily cap reached | `pending` again at the next UTC midnight, attempt not counted | unchanged |
  | recipient suppressed | `cancelled` | `failed / suppressed` |
  | send error | `pending` with backoff (60 s × attempt); `failed` after 3 attempts | `failed / send_failed` after the last attempt |
  | lead no longer eligible for this step | `cancelled` | unchanged |

- A classified reply cancels the lead's `pending` jobs in the same transaction that stops the lead (ADR 0013).
- The claim filters by workspace explicitly, in addition to RLS, because the local runtime role is a superuser that bypasses RLS.

## Consequences

- **At-least-once sending.** A send that is still in flight when its lease expires (more than 5 minutes) can be claimed by another worker and sent twice. A transaction commit that fails after the provider accepted the message has the same effect on the retry. At-least-once is the contract; the provider call is kept short so the window stays small.
- A job that is already `running` is not cancelled by a reply; it re-checks the lead state at the start of its own transaction.
- Any sender that runs this SQL and honours the payload can drain the queue.
- Queue latency is the worker poll interval; `LISTEN/NOTIFY` stays unused until a measured need.
