# ADR 0015 — Sending guards in the messaging send path

**Status:** accepted (Step 3)

## Context

Three guards were pulled into Step 3: never mail an address that unsubscribed or hard-bounced, never let two senders use one mailbox at the same moment, and keep each mailbox under a daily volume. They must apply to campaign sends and to `/send-test-email`, with Postgres only.

## Decision

- The guards live in `SendEmailHandler` in the messaging context — the one place every send goes through. Messaging is today's "Sending" slice; the campaign context reaches it through `EmailDispatchPort`.
- Order inside the send transaction:
  1. **Suppression.** The lower-cased recipient is in `messaging__suppressions` for the workspace → refuse.
  2. **Mailbox lock.** `pg_try_advisory_xact_lock(hashtext(mailbox_id))`; not acquired → busy. The lock is held until the job transaction ends.
  3. **Daily cap.** `count(*)` of the mailbox's sent outbound messages created since the start of the current **UTC calendar day** ≥ `mailbox__mailboxes.daily_send_cap` (default 20) → capped, retry at the next UTC midnight. No counter row, so nothing can drift. Test emails count too.
- Mapping: busy → retry in a few seconds; capped → retry at the next UTC midnight; neither counts as an attempt. Suppressed → the lead fails with `suppressed`. Over HTTP: suppressed → 409, busy or capped → 429.
- **Suppression sources**, written in the same poll transaction that classifies the reply:
  - The Gmail adapter flags a delivery-status notification: an `X-Failed-Recipients` header, a `mailer-daemon` or `postmaster` sender, or `Auto-Submitted` together with a delivery-status report part. The message gets intent `bounce` without calling the classifier, and the matched outbound recipient is suppressed as `hard_bounce`.
  - Intent `unsubscribe` suppresses the matched outbound recipient as `unsubscribe`.
- A bounce stops the lead as `failed / bounced`. Any other classified reply, including unsubscribe, pauses it.

## Consequences

- One code path enforces compliance and volume for every sender, including a future sender that calls an internal send endpoint.
- The UTC day is simple and predictable; it is not the mailbox owner's local day.
- An unmatched bounce (no outbound message found) is stored but suppresses nothing: the failed address is not known without parsing the report.
- Soft and hard bounce classes, a bounce-rate health signal and `HealthDegraded` are not built.
