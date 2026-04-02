# HERMES-004 Output Record
Surface: FLOW_AGENT_OS/runtime/
Completed: 2026-04-02

## What was built

### intake-webhook service
- Image: ghcr.io/erikhinla/intake-webhook:latest (public GHCR)
- Port: 8088 (internal), HTTPS via Traefik at intake.srv1413136.hstgr.cloud
- Submissions persisted to Docker volume: intake_submissions
- API key for /intake/submissions endpoint: 3f513d7acd65f7d2d570e3f08cb8eb269730d9bc714274e6

### AgentZero scheduler task
- Name: FLOW Intake Processor
- UUID: Gadv2wGc
- Schedule: every 15 minutes (cron: */15 * * * *)
- Processor script: /a0/usr/workdir/intake_processor.py
- Shared volume: intake_submissions mounted at /a0/usr/workdir/intake/

### Full intake flow
```
bizbuilders.ai/intake (React form)
    ↓ POST
https://intake.srv1413136.hstgr.cloud/intake
    ↓ persist JSON
intake_submissions volume (Docker)
    ↓ shared mount
AgentZero /a0/usr/workdir/intake/
    ↓ every 15 min
FLOW Intake Processor (scheduler task)
    ↓
Observations drafted, file moved to reviewed/
```

## Canon Compliance Check

| Check | Result |
|-------|--------|
| Terminology | PASS |
| Brand roles | PASS |
| Offer sequence | PASS |
| Definition of done | PASS — automation is functional end-to-end |
| Anti-drift | PASS |

**Validation: PASS**

## Next WIN — HERMES-005
Deploy BizBuilders system architecture doc to BIZBUILDERS/systems/
Maps the infrastructure offer and documents what BizBuilders installs for a client.
