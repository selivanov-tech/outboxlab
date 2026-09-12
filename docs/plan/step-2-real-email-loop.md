# Step 2 — Real email loop

[← Back to the plan](README.md)

**Status: code merged** on 2026-09-13 — [PR #2](https://github.com/selivanov-tech/outboxlab/pull/2) "Step 2: real email loop — Gmail send/receive, reply matching, intent classifier, outbox events". The live Gmail end-to-end run (the success signal below) still has to be executed by hand with real Google credentials.

## Goal

A real email round trip without a campaign engine: send through the Gmail API, detect the reply, classify its intent with a safe fallback.

## Success signal

Send an email to a controlled mailbox → reply from there → the poller catches the reply → the intent appears in the database and in `/debug/state`.

## Locked decisions

1. **Send and receive both go through the Gmail API**, with one OAuth token. No SMTP, no IMAP. The "last seen UID" from the original checklist became a provider-neutral sync cursor that the Gmail adapter maps to its history id. See [ADR 0004](../adr/0004-gmail-api-for-send-and-receive.md).
2. **Manual refresh-token auth.** Refresh token, client id and secret come from env / fly secrets; access tokens are minted at runtime. No OAuth web flow yet. Tokens are not encrypted at rest yet (parked).
3. **Intent classifier** (`positive`, `negative`, `ooo`, `unsubscribe`, `unclear`): the LLM path is primary and **on by default** (`LLM_ENABLED=true`), the deterministic classifier is the fallback. The provider is chosen by `LLM_PROVIDER` (`anthropic` | `openai`). The LLM activates only when the chosen provider's key is set and falls back to the rules on any API error, so a keyless environment stays offline. This replaced an earlier "off by default" decision once the bar became "any real human reply is classified correctly" — keyword-only rules return `unclear` for natural phrasing. See [ADR 0005](../adr/0005-llm-classifier-behind-a-port.md).
4. **Inline transactional outbox.** One poll cycle does `poll → match → classify → persist` in a **single transaction**; `InboundReceived`, `ReplyMatched`, `ReplyClassified` are written as rows in the outbox table. There is no dispatcher or relay yet; the first consumer arrives in Step 3. See [ADR 0006](../adr/0006-transactional-outbox-inline.md).
5. **The worker shares the api code but deploys separately.** It imports `app.*` directly and runs as `python -m app.entrypoints.worker` in its own process and its own fly app from the same image. The separate `apps/worker-py` project was folded into `apps/api`. See [ADR 0008](../adr/0008-worker-in-the-api-project.md).

## Design notes

**Tenancy**

- `mailboxes` is under RLS (unlike `workspaces`, the tenant registry). The worker sets the workspace GUC from `MAILBOX_WORKSPACE_ID`.
- New Google / LLM settings are optional (default empty), so the API starts without them and fails only on send / poll.

**Receiving**

- The first poll only sets the baseline cursor and processes nothing. Send the test email only after `/debug/state` shows a non-null sync cursor; otherwise the reply's history id is below the baseline and is never seen.
- Inbound filtering lives in the Gmail adapter: `fetch_new` drops `SENT`, non-`INBOX` and the mailbox's own messages, and returns only real inbound mail. The application handler knows nothing about labels; it only de-duplicates.
- Classification runs on the **body, not the snippet**. The receiver fetches the full message, takes the first `text/plain` part, cuts the quoted history (from the first `>` line, `On … wrote:`, `-----Original Message-----` or `From:`), truncates to about 2000 characters and passes it as a transient `body_text`. The short snippet is still stored for display. Reason: a snippet may miss the keyword or contain our own quoted text ("book a call") and produce a false positive.
- If Gmail reports the history as expired (worker was down for about a week or more) a warning is logged. A full re-sync is parked.

**Provider neutrality** — see [ADR 0009](../adr/0009-provider-neutral-names.md)

- Domain and ports use neutral names: `provider_message_id`, `provider_thread_id`, `sync_cursor`. Gmail specifics (`historyId`, `threadId`, labels) live only in `infrastructure/gmail/`.
- No provider discriminator column or adapter factory on the email side: the ports are already the seam, and a selector with a single value would be dead code. The LLM side does have a selector, because a second provider really exists.

**LLM client seam**

- `LlmClient` protocol (`async complete(prompt) -> str`) with `AnthropicChatClient` and `OpenAIChatClient` adapters inside the messaging context.
- One `LlmIntentClassifier` owns the prompt, the response parsing and the deterministic fallback, so nothing is duplicated per vendor. `IntentClassifierPort` does not know an LLM is involved.
- `factory.build_intent_classifier` reads `LLM_PROVIDER` and the matching key; no key or `LLM_ENABLED=false` → deterministic.

**Code layout** — see [ADR 0002](../adr/0002-modular-monolith-with-bounded-contexts.md)

- Bounded contexts moved under `app/contexts/<bc>/`; cross-cutting code in `app/shared/`; process roots flat in `app/entrypoints/` (`api.py`, `worker.py`, `seed.py`). Entrypoints are composition roots that cross context borders; per-context HTTP routes stay in `contexts/<bc>/presentation/`.

**Tables** — see [ADR 0007](../adr/0007-bc-prefixed-table-names.md)

- Every table is prefixed with its context: `identity__workspaces`, `campaign__campaigns`, `mailbox__mailboxes`, `messaging__outbound_messages`, `messaging__inbound_messages`, `messaging__outbox_events`.
- Migration `0002` (not yet deployed at the time) was edited in place so its tables are born with the prefix. Tables from `0001` (already deployed) are renamed by a new migration `0003`. Foreign keys and RLS policies follow the table by OID, so nothing else changes.

## What was built

- Contexts `identity`, `mailbox`, `messaging` (plus `campaign` as a table stub).
- Gmail API sender and receiver (`messaging/infrastructure/gmail/`).
- Reply matching by `In-Reply-To` / `References` with a normalised-subject fallback (`messaging/application/matching.py`).
- Intent classifier: deterministic rules plus LLM adapters for Anthropic and OpenAI behind a port.
- Transactional outbox writer and versioned event contracts in `contracts/events/{inbound_received,reply_matched,reply_classified}/v1.json`.
- Migrations `0002` (mailbox + messaging tables, RLS) and `0003` (context prefixes).
- Worker entrypoint `app/entrypoints/worker.py`; `apps/worker-py` removed.
- Routes: `POST /send-test-email` (needs `X-Workspace-Id`, non-production only), `/health`, `/version`, `/debug/state`, `/workspaces/me`.
- 98 tests; pyright and ruff clean; leak check and secret scan clean.
- On merge, the CI deploy ran migrations `0002` + `0003` on the production database through the fly release command.

## Live end-to-end runbook

1. Fill `.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GMAIL_USER_EMAIL`, `MAILBOX_WORKSPACE_ID` (the default value in `.env.example` matches the seeded workspace). For the "any real reply" bar also set the LLM key.
2. Mint the refresh token right before the run: in an OAuth "Testing" app it lives about 7 days. Scopes: `gmail.send` + `gmail.readonly`.
3. Use a **separate** mailbox as the recipient; the receiver ignores mail from the polled mailbox itself.
4. Order matters: `make restart` → `make seed` → wait until `/debug/state` shows a non-null sync cursor → only then `POST /send-test-email` with `X-Workspace-Id` → reply from the recipient → the worker picks the reply up within about 15–20 seconds.

## Parked (explicitly not Step 2)

Encrypted-at-rest tokens, the outbox dispatcher / relay (Step 3), full re-sync on an expired Gmail history cursor.
