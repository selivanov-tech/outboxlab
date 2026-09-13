# Step 5 — Go sender extraction

[← Back to the plan](README.md)

**Status: code merged** — PR_STEP_5. A live switch with real email is done by hand.

## Goal

Show that `Sending` really is the first candidate for extraction: a Go sender can replace the Python one without changing campaign or reply domain logic.

## Success signal

The worker implementation can be switched without changing campaign / reply domain logic.

- The switch is configuration only: `SENDER_IMPL=go` plus `make sender-go-up`.
- No file under `apps/api/app/contexts/*/domain` changed in this step.
- Both halves are tested. The Go claim runs against a migrated database in CI; the process route runs the same handler as the Python drain in integration tests.

## Checklist

- [x] Create `apps/sender-go`.
- [x] Read the same `send_jobs` table with `SELECT … FOR UPDATE SKIP LOCKED`: the claim statement is shared byte for byte ([`claim.sql`](../../contracts/jobs/send_job/claim.sql)).
- [x] Reuse the job payload contract frozen in Step 3 (`send_job` v1, strict decoding).
- [x] Cheapest path first: the Go worker calls an internal endpoint, `POST /internal/send-jobs/{job_id}/process`.
- [ ] If time allows: call the Gmail API directly from Go — not done; see "Next move" in [ADR 0018](../adr/0018-go-sender-claims-and-hands-off.md).
- [x] Feature flag or env switch: `SENDER_IMPL=python|go`.
- [x] README section comparing the two workers.

## Locked decisions (as built)

See [ADR 0018](../adr/0018-go-sender-claims-and-hands-off.md).

1. **Go claims, Python processes.** The Go sender runs the shared claim statement and posts each job to the internal route. The API processes a job only while it is `running` for that workspace, under a row lock, with the same handler as the Python drain. Go writes no job status.
2. **Failure means the lease decides.** Any error leaves the job `running`; it is claimed again after the 5-minute lease. The HTTP timeout is 1 minute.
3. **Switch.** `SENDER_IMPL=go` stops the Python drain; polling and reply dispatch keep running in the Python worker.
4. **The internal route is local only.** It needs `X-Internal-Token` and exists only when `INTERNAL_API_TOKEN` is set and `APP_ENV` is not `production`. **The production path for the Go sender is a later decision:** sender-side credentials or a private network between the fly apps. There is no prod image or fly app for the Go sender yet.
5. **Pins:** Go 1.26.2 in `go.mod`, pgx v5.11.0, `actions/setup-go@v7.0.0`.

## What was built

- `apps/sender-go`:
  - `internal/config`: environment variables; `DATABASE_URL` may use the Python `+asyncpg` scheme.
  - `internal/queue`: the claim with the workspace setting, and strict payload decoding.
  - `internal/api`: the client for the internal route.
  - `cmd/sender`: the loop with jitter, graceful shutdown and JSON logs (job, lead, step, attempt, outcome, queue latency, duration).
- Python:
  - `contracts/jobs/send_job/claim.sql` is the single claim statement; a contract test checks the Python constant against it.
  - `SendJobRepository.get_claimed` locks the row.
  - `ProcessSendJobByIdHandler` and the internal route.
  - `SENDER_IMPL` and `INTERNAL_API_TOKEN` settings; the worker switch and its start-up summary.
- Local: `docker compose --profile go-sender`, `make sender-go-up`, `make sender-go-logs`, `make sender-go-test`.
- CI: a `sender-go` job (gofmt, vet, test, build) in the deploy gate, and a Go claim test step in `api-tests` after migrations (about 10 lines of workflow).

## Changes compared with the plan

- The internal endpoint processes a claimed job by id (`/internal/send-jobs/{job_id}/process`) instead of a generic `/internal/send`, so the guards, the lead state and the job status stay in one handler.
- The API locks the job row while processing, so two processes cannot finish the same claimed job.
- The claim statement became a shared contract file, not only a copy of the documented SQL.
- The Go claim integration test runs in CI, inside the existing `api-tests` job.

## Switch the sender (local)

1. In `.env`: `SENDER_IMPL=go` and a long random `INTERNAL_API_TOKEN` (for example `openssl rand -hex 32`); `MAILBOX_WORKSPACE_ID` must be set.
2. `make restart` — the API mounts the internal route, and the worker logs `send jobs left to the go sender`.
3. `make sender-go-up`, then `make sender-go-logs`: `sender started`, then one `send job processed` line per job, with `outcome`.
4. Run the demo or `make smoke SMOKE_LEAD_EMAIL=<lead-address>`. The lead goes `sent`, then `paused` after the reply — the same result as with the Python sender.
5. Back to Python: `SENDER_IMPL=python`, `docker compose … --profile go-sender stop sender-go`, `make restart`.

## Known gaps

- No production path for the Go sender (see decision 4).
- Gmail is still called from Python.
- A send still in flight after its lease can run twice ([ADR 0014](../adr/0014-send-job-queue-contract.md)); the row lock only prevents two concurrent process calls for the same claim.
- Go metrics are structured logs for now; `/metrics` is Step 7 for the Python processes.
