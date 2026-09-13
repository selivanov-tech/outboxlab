# ADR 0018 — Go sender: claim in Go, process behind an internal route

**Status:** accepted (Step 5)

## Context

Sending is the first extraction candidate. Step 3 froze the send-job queue contract ([ADR 0014](0014-send-job-queue-contract.md)). The lead state machine, the sending guards ([ADR 0015](0015-sending-guards-in-messaging.md)) and the Gmail adapter live in the Python code. The step must show that a second implementation can drain the queue without any change to the campaign or reply domain, at the lowest cost.

## Decision

- **`apps/sender-go`** (Go 1.26.2, pgx v5) is a separate service. It claims due jobs in its own transaction: it sets the workspace for row-level security, then runs the claim statement from [`contracts/jobs/send_job/claim.sql`](../../contracts/jobs/send_job/claim.sql). The Python and Go constants must equal that file byte for byte; both test suites check it. pgx needs `@name` arguments, so the Go code rewrites `:name` to `@name` at start-up, and a test proves nothing else changes.
- Payloads are decoded strictly against `send_job` v1: every field present, no unknown fields, `job_version` 1.
- **Processing stays in Python.** For each claimed job the Go sender calls `POST /internal/send-jobs/{job_id}/process` with `X-Workspace-Id` and `X-Internal-Token`. The API loads the job only if it is still `running` for that workspace, locks the row (`FOR UPDATE`) and runs the same `ProcessClaimedSendJobHandler` the Python drain uses: guards, Gmail send, lead state, next step, job status. The Go sender never writes a job status, so one state machine owns every transition.
- **Failures.** A network error or a non-2xx answer is logged; the job stays `running` and is claimed again when its lease expires. `409` means the job is no longer claimed, for example because another process already finished it.
- **Switch.** `SENDER_IMPL=python|go`. With `go` the Python worker keeps polling the inbox and dispatching replies but does not drain send jobs. Both senders at once are still safe (`SKIP LOCKED` plus the row lock), but that is not a supported setup.
- **Exposure.** The internal route exists only when `INTERNAL_API_TOKEN` is set and `APP_ENV` is not `production`. How a Go sender reaches the API in production — sender-side credentials or a private network — is a later decision and is not built.
- **Pins.** `go 1.26.2` in `go.mod`; CI uses `actions/setup-go@v7.0.0` with the version from `go.mod`. A `sender-go` job (gofmt, vet, test, build) is part of the deploy gate, and `api-tests` runs the Go claim test against the freshly migrated database.

## Consequences

- **What moved:** the claim loop, the process boundary and the runtime. **What stayed behind the contract:** the lead state machine, the guards, the Gmail adapter, reply handling and the schema. No file under `contexts/*/domain` changed in this step.
- One extra HTTP call per job. The HTTP timeout (1 minute) is shorter than the lease (5 minutes), so a slow call gives up before another sender can claim the job.
- The next extraction move — calling Gmail from Go — would have to take the guards and the outbound-message record with it, or expose them. That is a real extraction of the messaging send path, not a transport change.
