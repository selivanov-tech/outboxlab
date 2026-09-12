# Step 3 — Campaign state machine

[← Back to the plan](README.md)

**Status: planned.**

## Goal

Turn the email loop into a domain proof: a campaign sends an email, the reply is classified, the lead is paused, future sends are cancelled.

## Success signal

Campaign sends an email → reply is classified → the lead becomes `PAUSED` and its future sends are cancelled.

## Checklist

**Core**

- [ ] `Campaign` aggregate with `Step` and `Lead`; lead states `PENDING`, `SCHEDULED`, `SENT`, `PAUSED`, `DONE`, `FAILED`. `Lead.state` changes only through the aggregate.
- [ ] Minimal sequence: step 1 immediately, step 2 scheduled later.
- [ ] `send_jobs` queue in Postgres, claimed with `SELECT … FOR UPDATE SKIP LOCKED`.
- [ ] The Python worker drains `send_jobs`.
- [ ] Freeze the job payload contract so the Step 5 Go sender can reuse it.
- [ ] Rate limit v0: advisory lock per mailbox plus a `sent_today` counter.
- [ ] `on_reply_classified` handler (the first outbox consumer) calls `Campaign.pause_lead()` and cancels future jobs for that lead.
- [ ] Smoke test on a production-like environment: one campaign, one lead, one mailbox.
- [ ] README draft: architecture diagram, demo path, trade-offs, what is intentionally not built.

**Scope added after the Step 2 review** — three cheap, high-signal pieces that production outreach tools treat as first-class (bounce webhooks, `hard_bounce` suppression reasons, stop rules on bounce thresholds, per-mailbox daily volume):

- [ ] **3a. Bounce as a first-class signal.** Today a delivery-status notification from `mailer-daemon` passes the receiver filters, matches the original send by `References`, and the classifier returns `unclear` — which in Step 3 would pause the lead and make a dead address look engaged. Detect it in the Gmail adapter (`Auto-Submitted: auto-replied`, sender `mailer-daemon` / `postmaster`, `Content-Type: message/delivery-status`), add a `bounce` intent value, and route it away from the reply → pause path: mark the lead / address dead and feed suppression.
- [ ] **3b. Suppress on unsubscribe.** The classifier already detects `unsubscribe`; make it a hard stop and add a small suppression check before every send. Hard bounces feed the same table. Minimal shape: a suppressions table keyed by `email + reason`.
- [ ] **3c. Per-mailbox daily count and cap.** The main domain constraint: volume = domains × mailboxes × roughly 20 sends per mailbox per day. One per-mailbox daily counter and a cap on send, Postgres-only (a counter row or `count(*)` of today's sends); reject or queue when exceeded. This is the production version of "rate limit v0" above.

## Known gaps to mention in the README (not to build now)

- `match_reply` computes candidates once per poll and does not remove a matched outbound message inside the batch; the subject-equality fallback can mis-match with more than one lead. Fine for a one-lead demo. Before a demo with several leads in frame, remove the matched candidate inside the batch (a five-line fix).
- `POST /send-test-email` is not idempotent (a double POST is a double send). A real API would use an `Idempotency-Key` on mutations.
