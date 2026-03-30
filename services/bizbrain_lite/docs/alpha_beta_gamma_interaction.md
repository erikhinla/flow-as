# Alpha Beta Gamma Interaction

BizBrain Lite is the control plane for handoffs, task state, and artifact traceability.

## Alpha

- Creates and updates tasks.
- Publishes artifacts as execution outputs.
- Sends frequent heartbeat updates.
- Typical endpoints:
  - `POST /v1/tasks`
  - `PATCH /v1/tasks/{task_id}`
  - `POST /v1/artifacts`
  - `POST /v1/agents/{agent_id}/heartbeat`

## Beta

- Coordinates cross-thread context and transitions.
- Creates handoff records with context summaries.
- Updates thread state and active task pointers.
- Typical endpoints:
  - `POST /v1/handoffs`
  - `POST /v1/handoffs/{handoff_id}/ack`
  - `PATCH /v1/threads/{thread_id}`

## Gamma

- Handles high-risk transitions and approval gates.
- Uses `risk_level=gamma` for critical handoffs.
- Confirms acknowledgment before irreversible transitions.
- Typical endpoints:
  - `POST /v1/handoffs` with `risk_level=gamma`
  - `POST /v1/handoffs/{handoff_id}/ack`
  - `PATCH /v1/tasks/{task_id}` to move blocked -> completed/failed

