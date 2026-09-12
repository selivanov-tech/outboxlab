# ADR 0012 — No code for future use

**Status:** accepted (Step 1)

## Context

The target context map (see the architecture overview) names six contexts, several ports and many tables. Scaffolding all of them up front produces empty modules, unused ports and tables nobody writes to — dead code on arrival that still has to be maintained.

## Decision

A module, port, helper or table exists only when something calls or writes it today. Step 1 therefore shipped only `identity` (plus a `campaign` table stub with an RLS smoke test), and deleted the pre-created `mailbox`, `sending` and `reply` packages. Each returns with its first real consumer; the plan pages record when.

## Consequences

- The code is smaller than the plan at every point in time, and every file has a caller.
- The plan and the ADRs, not the code, carry the future shape.
- Refactors happen when the second use appears, with real requirements in hand.
