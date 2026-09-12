# ADR 0004 — Gmail API for both send and receive

**Status:** accepted (Step 2)

## Context

The original checklist had SMTP for sending and IMAP polling with a "last seen UID" for replies. That means two protocols, two credentials paths and two failure modes for one mailbox.

## Decision

Both directions use the Gmail API with one OAuth refresh token (scopes `gmail.send` + `gmail.readonly`). Sending stores the RFC 822 `Message-ID` and the provider's message and thread ids. Receiving polls with a provider-neutral `sync_cursor`, which the Gmail adapter maps to its history id; the first poll only sets the baseline. Inbound filtering (drop `SENT`, non-`INBOX`, and the mailbox's own mail) lives in the adapter.

Auth is a manual refresh-token flow: client id, secret and refresh token come from env / fly secrets and access tokens are minted at runtime. No OAuth web flow, no encrypted-at-rest storage yet (both parked).

## Consequences

- One credential, one client, one adapter pair behind `EmailSenderPort` / `EmailReceiverPort`.
- A refresh token minted in an OAuth "Testing" app expires after about a week; the live end-to-end run must mint it right before.
- If Gmail's history window has expired, the adapter logs a warning; a full re-sync is parked.
- A second mail provider is a new adapter pair, not a domain change (see ADR 0009).
