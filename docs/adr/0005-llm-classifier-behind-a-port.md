# ADR 0005 — Intent classifier: LLM behind a port with a deterministic fallback

**Status:** accepted (Step 2; replaces an earlier "LLM off by default")

## Context

Reply intent (`positive`, `negative`, `ooo`, `unsubscribe`, `unclear`) drives the campaign state machine. Keyword rules are cheap and offline but return `unclear` for most natural phrasing. An LLM is accurate but is an external dependency that must never break the demo.

## Decision

- `IntentClassifierPort` is the only thing the application sees.
- `LlmIntentClassifier` owns the prompt, response parsing and the deterministic fallback. It talks to an `LlmClient` protocol (`async complete(prompt) -> str`) with adapters for Anthropic and OpenAI.
- The provider is chosen by `LLM_PROVIDER`; the classifier activates only when `LLM_ENABLED=true` **and** that provider's key is set. Any API error falls back to the rules.
- `LLM_ENABLED` defaults to **true**. The earlier "off by default" was reversed once the bar became "any real human reply is classified correctly"; a keyless environment (CI, bare demo) is still fully offline.
- Classification reads the de-quoted message body, not the snippet, so quoted history cannot trigger false positives.

## Consequences

- Vendor lock-in is a one-file adapter; the prompt and parsing are not duplicated per vendor.
- A provider selector is justified here because a second provider really exists (contrast ADR 0009 for email).
- Cost is negligible: one short prompt per inbound message, a one-word answer.
