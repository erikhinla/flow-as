# Redis Usage

Redis is the runtime state layer for low-latency control-plane reads/writes.

## Key schema

- `bizbrain:task:{task_id}` JSON object
- `bizbrain:task:{task_id}:events` JSON event list
- `bizbrain:artifact:{artifact_id}` JSON object
- `bizbrain:thread:{thread_id}` JSON object
- `bizbrain:index:task_by_thread:{thread_id}` set of task IDs
- `bizbrain:handoff:{handoff_id}` JSON object
- `bizbrain:agent:{agent_id}:status` JSON object

## TTL

- Agent status heartbeat key: 600 seconds
- Active tasks, artifacts, threads, handoffs: 72 hours
- Event lists: no TTL, list trimmed to most recent 1000 entries

## Rehydration behavior

- Redis is runtime-first and ephemeral.
- PostgreSQL is the durable FLOW state layer.
- Redis holds the fast operational view and queue-adjacent state.

