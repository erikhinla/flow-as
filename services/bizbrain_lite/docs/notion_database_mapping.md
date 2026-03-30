# Notion Database Mapping

BizBrain Lite mirrors runtime registry records into Notion for durable operational memory.

## Databases

## 1) Tasks DB

- `task_id`
- `title`
- `source`
- `status`
- `priority`
- `owner_agent`
- `thread_id`
- `repo_path`
- `created_at`
- `updated_at`

## 2) Artifacts DB

- `artifact_id`
- `task_id`
- `type`
- `path_or_url`
- `checksum`
- `producer_agent`
- `campaign`
- `created_at`
- `updated_at`

## 3) Thread Handoffs DB

- `handoff_id`
- `thread_id`
- `from_agent`
- `to_agent`
- `reason`
- `context_summary`
- `risk_level`
- `acknowledged_at`
- `created_at`
- `updated_at`

## 4) Agent Status Log DB

- `agent_id`
- `state`
- `current_task_id`
- `heartbeat_at`
- `queue_depth`
- `last_error`
- `capabilities`
- `updated_at`

## 5) Operational Memory DB

- `thread_id`
- `category`
- `content`
- `source`
- `status`
- `created_at`

