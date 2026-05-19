# Notion → FLOW Agent AS Bridge Runbook

## Verdict

The missing layer is the submission bridge, not the Notion task record and not the agent prompt.

This bridge polls Notion directly and submits matching tasks into FLOW intake. It removes Activepieces from the critical path until Activepieces is proven reliable.

## Bridge file

`scripts/notion-flow-bridge.mjs`

## Required environment

```bash
export NOTION_TOKEN="secret_xxx"
export NOTION_TASKS_DATABASE_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export FLOW_INTAKE_URL="http://127.0.0.1:18000/v1/intake/task"
export FLOW_API_TOKEN="your-flow-api-token"
```

Optional:

```bash
export POLL_INTERVAL_MS="30000"
export DEFAULT_OWNER="agent_zero"
export LOG_LEVEL="info"
export BRIDGE_ONCE="true"
```

## What it watches

Notion database: `Tasks FAAS`

It submits pages where:

- `Status` equals `Submitted`
- `FLOW Job ID` is empty

## What it sends to FLOW

```json
{
  "task_id": "<Task ID or Notion page id>",
  "task_name": "<Task Name>",
  "task_type": "<Task Type>",
  "risk_tier": "<Risk Tier>",
  "priority": "<Priority>",
  "preferred_owner": "<Preferred Owner>",
  "output_required": "true",
  "goal": "<Goal>",
  "inputs": {},
  "source": {
    "system": "notion",
    "database": "Tasks FAAS",
    "notion_page_id": "<page id>",
    "notion_url": "<page url>"
  }
}
```

## What it writes back on success

- `Status` → `Activated`
- `FLOW Job ID` → returned `job_id`, `flow_job_id`, `id`, or `task_id`
- `Submitted At` → current timestamp
- `Last Error` → cleared

## What it writes back on failure

- `Status` → `Failed`
- `Last Error` → HTTP status / response body / exception message

## One-shot test

Run this from the VPS where FLOW intake is reachable:

```bash
cd /opt/flow-as
export BRIDGE_ONCE=true
node scripts/notion-flow-bridge.mjs
```

Expected proof:

1. Notion record with `Status=Submitted` and empty `FLOW Job ID` is found.
2. Terminal logs `submitting_task_to_flow`.
3. Terminal logs `task_submitted_to_flow`.
4. The same Notion record changes to `Status=Activated`.
5. The same Notion record has a populated `FLOW Job ID`.

## Long-running mode

```bash
cd /opt/flow-as
unset BRIDGE_ONCE
node scripts/notion-flow-bridge.mjs
```

## Docker Compose service

Add this service to the stack after the repo is present on the VPS:

```yaml
  notion-flow-bridge:
    image: node:20-alpine
    container_name: notion-flow-bridge
    working_dir: /app
    command: ["node", "scripts/notion-flow-bridge.mjs"]
    restart: unless-stopped
    volumes:
      - /opt/flow-as:/app:ro
    environment:
      NOTION_TOKEN: ${NOTION_TOKEN}
      NOTION_TASKS_DATABASE_ID: ${NOTION_TASKS_DATABASE_ID}
      FLOW_INTAKE_URL: ${FLOW_INTAKE_URL:-http://flow-orchestrator:8000/v1/intake/task}
      FLOW_API_TOKEN: ${FLOW_API_TOKEN}
      POLL_INTERVAL_MS: ${POLL_INTERVAL_MS:-30000}
      DEFAULT_OWNER: ${DEFAULT_OWNER:-agent_zero}
      LOG_LEVEL: ${LOG_LEVEL:-info}
    networks:
      - flow-network
```

If the intake service is exposed only on the host as `127.0.0.1:18000`, use this instead inside Docker:

```bash
FLOW_INTAKE_URL=http://host.docker.internal:18000/v1/intake/task
```

On Linux, add this under the service if needed:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Acceptance criteria

Bridge is not complete until all are true:

- At least 3 Notion-created tasks move from `Submitted` to `Activated` without terminal submission.
- Each task receives a `FLOW Job ID`.
- FLOW intake logs show accepted submissions.
- Hermes or Agent Zero dequeues and completes the tasks.
- Notion receives final `Done` or `Failed` writeback from the executor layer.

## Important boundary

This bridge proves Notion → FLOW intake. It does not by itself prove agent execution. Agent execution is proven only when the worker updates the task to `Done` and produces an artifact or dashboard-visible output.
