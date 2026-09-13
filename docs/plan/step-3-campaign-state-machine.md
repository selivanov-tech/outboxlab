# Step 3 — Campaign state machine

[← Back to the plan](README.md)

**Status: code merged** in two stacked pull requests — [PR #4](https://github.com/selivanov-tech/outboxlab/pull/4) (aggregate, send queue, sending guards, campaign API) and [PR #10](https://github.com/selivanov-tech/outboxlab/pull/10) (bounce and unsubscribe signals, reply consumer, docs). The live Gmail run of a campaign (runbook below) is done by hand with real credentials.

## Goal

Turn the email loop into a domain proof: a campaign sends an email, the reply is classified, the lead is paused, future sends are cancelled.

## Success signal

Campaign sends an email → reply is classified → the lead becomes `PAUSED` and its future sends are cancelled.

Covered in CI by `tests/integration/campaign/test_reply_pauses_lead_end_to_end.py`: create a two-step campaign, add a lead, start, drain the queue, poll a reply to step 1 (classified by the deterministic rules), dispatch → the lead is `paused` with intent `positive`, the step-2 job is `cancelled`, and draining after the follow-up delay sends nothing.

## Checklist

**Core**

- [x] `Campaign` aggregate with `Step` and `Lead`; lead states `PENDING`, `SCHEDULED`, `SENT`, `PAUSED`, `DONE`, `FAILED`. `Lead.state` changes only through the aggregate.
- [x] Minimal sequence: step 1 immediately, step 2 scheduled later (`delay_seconds` per step).
- [x] `send_jobs` queue in Postgres, claimed with `SELECT … FOR UPDATE SKIP LOCKED`.
- [x] The Python worker drains `send_jobs`.
- [x] Freeze the job payload contract so the Step 5 Go sender can reuse it: [`contracts/jobs/send_job/v1.json`](../../contracts/jobs/send_job/v1.json).
- [x] Rate limit v0: advisory lock per mailbox plus a daily count (see 3c).
- [x] `on_reply_classified` handler (the first outbox consumer) stops the lead and cancels its future jobs.
- [x] Production-like smoke test: one campaign, one lead, one mailbox — the end-to-end integration test above; the live Gmail run is the manual runbook below.
- [x] README draft: architecture diagram, demo path, trade-offs, what is intentionally not built.

**Scope added after the Step 2 review**

- [x] **3a. Bounce as a first-class signal.** The Gmail adapter flags delivery-status notifications (`X-Failed-Recipients`, `mailer-daemon` / `postmaster` senders, `Auto-Submitted` with a delivery-status report part). A bounce gets intent `bounce` without calling the classifier, suppresses the address and fails the lead instead of pausing it.
- [x] **3b. Suppress on unsubscribe.** An `unsubscribe` reply writes a suppression row; every send checks suppressions first. Hard bounces feed the same table (`messaging__suppressions`, unique on workspace + email + reason).
- [x] **3c. Per-mailbox daily count and cap.** `mailbox__mailboxes.daily_send_cap` (default 20) against `count(*)` of today's sent messages. The window is the **UTC calendar day**. A capped job waits until the next UTC midnight.

## Locked decisions (as built)

1. **Lead states.** `pending` — added, campaign not started. `scheduled` — step-1 job queued. `sent` — at least one step sent, the next one queued. `done` — last step sent. `paused` — a reply was classified (any intent except bounce); allowed from `sent` and `done`. `failed` — bounced, suppressed at send time, or the send failed three times. The lead also keeps `steps_sent`, `stop_reason` (`replied`, `unsubscribed`, `bounced`, `suppressed`, `send_failed`) and `reply_intent`.
2. **Queue contract** — [ADR 0014](../adr/0014-send-job-queue-contract.md). Statuses `pending / running / done / failed / cancelled`. The claim also takes a `running` job whose 5-minute lease expired. The caller passes the clock. Retries back off 60 s × attempt and give up after 3 attempts.
3. **Sending guards live in the messaging send path** — [ADR 0015](../adr/0015-sending-guards-in-messaging.md). Order: suppression → advisory transaction lock per mailbox → daily cap. Busy and capped jobs are deferred without counting an attempt.
4. **First outbox consumer** — [ADR 0013](../adr/0013-outbox-consumer-processed-events.md). A step of the worker tick (poll → dispatch → drain) with a processed-events set, not an offset. `ReplyClassified` v2 adds `event_version`, `matched_outbound_id` and the `bounce` intent; v1 events are acknowledged without changes.
5. **Reply matching is stricter.** The subject fallback also requires the inbound sender to be the outbound recipient, and a matched outbound message is removed from the batch. With many leads on one template subject, a reply can no longer pause another lead.
6. **Campaign routes are non-production only**, like `/send-test-email`: the API has no auth yet, and a public send endpoint would let anyone send from the connected mailbox.

## What was built

- Campaign context: domain (`Campaign`, `Step`, `Lead`, `SendJob`), repositories, commands (`create`, `add leads`, `start` — idempotent), queries (list with lead counts by state, detail with each lead's next send time), the send-job queue, the reply consumer.
- Routes: `POST /campaigns`, `POST /campaigns/{id}/leads`, `POST /campaigns/{id}/start`, `GET /campaigns`, `GET /campaigns/{id}`; `/debug/state` adds lead and job counts; `/send-test-email` answers 409 for a suppressed recipient and 429 for a busy or capped mailbox.
- Messaging: suppressions, advisory lock, daily cap, bounce detection, unsubscribe suppression, `ReplyClassified` v2.
- Worker tick: poll inbox → dispatch classified replies → drain send jobs.
- Migrations `0004` (campaign steps, leads, send jobs, suppressions, mailbox daily cap, `campaign__campaigns.mailbox_id`) and `0005` (processed events, outbox index). All new tenant tables are under RLS.
- Contracts: `contracts/jobs/send_job/v1.json`, `contracts/events/reply_classified/v2.json`; tests validate real payloads against both with `jsonschema` (dev dependency only).
- 187 tests; pyright and ruff clean; leak check and secret scan clean.

## Changes compared with the plan

- Shipped as two stacked PRs instead of one, to keep each diff reviewable.
- No `sent_today` counter row: the cap counts today's sent messages, which cannot drift.
- `delay_seconds` instead of days, so a short demo can show the follow-up being scheduled and cancelled.
- The queue gained a `cancelled` status and a lease; the claim filters by workspace explicitly.
- Unsubscribe pauses the lead (reason `unsubscribed`) in addition to suppressing the address; bounce fails the lead.
- No campaign-side outbox events (`LeadPaused` …): nothing consumes them yet, the lead row is the record.
- Two migrations (`0004`, `0005`), one per PR.

## Known gaps (documented, not built)

- **At-least-once sending.** A send still in flight after its 5-minute lease, or a commit that fails after Gmail accepted the message, can lead to a second send on retry.
- A delivery failure that cannot be matched to an outbound message is stored but suppresses nothing.
- Bounce detection is tested on fixtures shaped like Gmail notifications, not on a live bounce.
- Follow-ups are new messages, not replies in the same Gmail thread; replies to either step still match by `Message-ID`.
- The worker serves one workspace (`MAILBOX_WORKSPACE_ID`); the local runtime role is a superuser, which is why the queue and the consumer filter by workspace explicitly.
- `POST /send-test-email` is still not idempotent.

## Live campaign runbook (manual, real credentials)

1. `.env` has the Gmail values and `MAILBOX_WORKSPACE_ID` (see the Step 2 runbook). Use a **separate** recipient mailbox you control as the lead.
2. `make restart` → `make migrate` → `make seed`. Wait until `GET /debug/state` shows a non-null `mailbox_last_sync_cursor`.
3. Create and start a campaign (replace the placeholders):

   ```bash
   API=https://<api-domain>
   WS="X-Workspace-Id: <workspace-id>"
   CAMPAIGN=$(curl -s -X POST "$API/campaigns" -H "$WS" -H 'content-type: application/json' \
     -d '{"name":"Live check","steps":[{"subject":"Quick question","body":"Hi!","delay_seconds":0},{"subject":"Re: Quick question","body":"Following up","delay_seconds":600}]}' \
     | python3 -c 'import sys, json; print(json.load(sys.stdin)["id"])')
   curl -s -X POST "$API/campaigns/$CAMPAIGN/leads" -H "$WS" -H 'content-type: application/json' -d '{"emails":["<lead-address>"]}'
   curl -s -X POST "$API/campaigns/$CAMPAIGN/start" -H "$WS"
   ```

4. Within one worker tick (`make logs`): `send job … step 1: sent`. `GET /campaigns/$CAMPAIGN` shows the lead `sent` with a `next_send_at`.
5. Reply from the lead mailbox, for example "Yes, interested — let's talk".
6. Within about 20 seconds the log shows `lead … is paused … future sends cancelled`; `GET /campaigns/$CAMPAIGN` shows `paused`, `reply_intent: positive`, no `next_send_at`; no second email arrives after the delay.
