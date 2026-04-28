 # API Endpoint List

Base path: `/v1`

## Health and metadata

- `GET /health`
- `GET /capabilities`

## Tasks

- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `PATCH /tasks/{task_id}`
- `POST /tasks/{task_id}/events`
- `GET /tasks/{task_id}/events`
- `GET /tasks/{task_id}/artifacts`

## Artifacts

- `POST /artifacts`
- `GET /artifacts`
- `GET /artifacts/{artifact_id}`
- `GET /artifacts/by-task/{task_id}`

## Handoffs

- `POST /handoffs`
- `GET /handoffs`
- `POST /handoffs/{handoff_id}/ack`

## Threads

- `POST /threads`
- `GET /threads/{thread_id}`
- `PATCH /threads/{thread_id}`

## Agent status

- `POST /agents/{agent_id}/heartbeat`
- `GET /agents`
- `GET /agents/{agent_id}`
- `PATCH /agents/{agent_id}/status`

