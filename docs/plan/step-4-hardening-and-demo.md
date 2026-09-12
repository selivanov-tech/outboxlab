# Step 4 — Hardening and demo

[← Back to the plan](README.md)

**Status: planned.**

## Goal

No big features. Stabilise, package, record a short demo, finish README v1.

## Checklist

- [ ] Minimal read-only state viewer: campaigns, leads, statuses, reply intent. Creating a campaign may stay an API / script call.
- [ ] Smoke-test checklist on the deployed URL: health, database, mailbox, send, reply, pause.
- [ ] Check cold start and logs on fly.io.
- [ ] Remove obvious demo breakers: hard-coded local URLs, missing env vars, fragile seed data.
- [ ] README v1 finalised: demo path, architecture, trade-offs, screenshots, run instructions.
- [ ] Demo video (about 3 minutes): deployed URL → create campaign → send → reply → paused lead → a short look at the code and architecture. If the UI is not ready, drive it through the API and `/debug/state`.
- [ ] Write down what worked, what was intentionally deferred, and the next three tasks.

## Artifacts

Live demo URL, demo video, README v1.

## Success signal

The live demo works, the video is recorded, the README is ready.
