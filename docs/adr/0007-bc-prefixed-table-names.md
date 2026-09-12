# ADR 0007 — Every table is prefixed with its bounded context

**Status:** accepted (Step 2)

## Context

With several contexts in one database, a bare table name (`messages`, `events`) does not say who owns the data.

## Decision

Tables are named `{bc}__{table}`: `identity__workspaces`, `campaign__campaigns`, `mailbox__mailboxes`, `messaging__outbound_messages`, `messaging__inbound_messages`, `messaging__outbox_events`. The prefix goes into `__tablename__`, the `ForeignKey` target and the migration. Index and constraint names keep their plain form.

Migration history only moves forward: a migration that has not shipped is edited in place; tables from a shipped migration are renamed by a new migration (`0003`). Foreign keys and RLS policies follow the table by OID.

## Consequences

- Ownership is visible in any SQL client and in every migration.
- Cross-context foreign keys stand out by name and can be questioned in review.
