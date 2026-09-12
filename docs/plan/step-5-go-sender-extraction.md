# Step 5 — Go sender extraction

[← Back to the plan](README.md)

**Status: planned.**

## Goal

Show that `Sending` really is the first candidate for extraction: a Go sender can replace the Python one without changing campaign or reply domain logic.

## Checklist

- [ ] Create `apps/sender-go`.
- [ ] Read the same `send_jobs` table with `SELECT … FOR UPDATE SKIP LOCKED`.
- [ ] Reuse the job payload contract frozen in Step 3.
- [ ] Cheapest path first: the Go worker calls an internal `POST /internal/send`. If time allows: call the Gmail API directly from Go.
- [ ] Feature flag or env switch: Python sender vs Go sender.
- [ ] README section comparing the two workers: what changed, what stayed behind the contract.

## Artifacts

`apps/sender-go`, README extraction story, a short demo of switching the sender implementation.

## Success signal

The worker implementation can be switched without changing campaign / reply domain logic.
