# FLOW Smoke Test Runbook

## Purpose

Verify that the minimal FLOW Agent AS deployment is live and can accept, route, and track work.

## Assumptions

- the stack is running through `docker compose`
- BizBrain Lite is exposed on port `18000`
- Agent Zero is exposed on port `50080`
- Postiz is exposed on port `5000`
- Portainer is exposed on port `9443`

Set your host before running the checks:

```bash
export FLOW_HOST=http://YOUR_HOST_OR_IP:18000
export FLOW_TOKEN=your_bizbrain_api_token_here
```

## 1. Basic service health

```bash
curl "$FLOW_HOST/v1/health"
curl "$FLOW_HOST/v1/flow/health"
curl "$FLOW_HOST/v1/intake/status"
curl "$FLOW_HOST/v1/intake/queues/status"
```

Expected:

- HTTP `200`
- `service` is `bizbrain-lite`
- `redis_ok` is `true`
- `postgres_ok` is `true`
- FLOW health is not `unhealthy`

## 2. Submit a bounded task envelope

```bash
TASK_ID=$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)

curl -X POST "$FLOW_HOST/v1/intake/task" \
  -H "Content-Type: application/json" \
  -d "{
    \"task_id\": \"$TASK_ID\",
    \"created_at\": \"2026-04-18T12:00:00Z\",
    \"source\": \"manual\",
    \"title\": \"Draft launch-day hero copy\",
    \"goal\": \"Produce bounded launch-day homepage hero copy and CTA options for tomorrow's release.\",
    \"task_type\": \"content_prep\",
    \"risk_tier\": \"low\",
    \"preferred_owner\": \"hermes\",
    \"inputs\": {
      \"notes\": \"Focus on launch readiness, confidence, and urgency.\"
    },
    \"output_required\": \"Persisted hero-copy draft ready for review\",
    \"review_required\": false,
    \"rollback_required\": false,
    \"status\": \"pending\"
  }"
```

Expected:

- `status` is `accepted`
- `owner` is returned
- `queue` is returned

## 3. Confirm queue movement

```bash
curl "$FLOW_HOST/v1/intake/queues/status"
curl "$FLOW_HOST/v1/flow/health"
```

Expected:

- queue depth increases for the selected owner
- FLOW health reflects queued work

## 4. Check protected registry endpoint

```bash
curl "$FLOW_HOST/v1/agents" -H "x-api-token: $FLOW_TOKEN"
```

Expected:

- HTTP `200` when token matches
- HTTP `401` when token is missing or wrong

## 5. Check human-facing surfaces

Open these in a browser:

- `http://YOUR_HOST_OR_IP:18000/docs`
- `http://YOUR_HOST_OR_IP:50080`
- `http://YOUR_HOST_OR_IP:5000`
- `https://YOUR_HOST_OR_IP:9443`

Expected:

- BizBrain Lite OpenAPI docs load
- Agent Zero login page loads
- Postiz login or registration loads
- Portainer login loads

## 6. Optional high-risk gate check

Submit a high-risk implementation task and confirm it blocks without review artifacts.

```bash
HIGH_RISK_ID=$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)

curl -X POST "$FLOW_HOST/v1/intake/task" \
  -H "Content-Type: application/json" \
  -d "{
    \"task_id\": \"$HIGH_RISK_ID\",
    \"created_at\": \"2026-04-18T12:05:00Z\",
    \"source\": \"manual\",
    \"title\": \"Prepare production launch deployment\",
    \"goal\": \"Prepare a bounded production deployment task with rollback and review requirements.\",
    \"task_type\": \"implementation\",
    \"risk_tier\": \"high\",
    \"preferred_owner\": \"agent_zero\",
    \"inputs\": {
      \"notes\": \"This task should require review gating.\"
    },
    \"output_required\": \"Deployment-ready change package with explicit rollback\",
    \"review_required\": true,
    \"rollback_required\": true,
    \"status\": \"pending\"
  }"

curl -X POST "$FLOW_HOST/v1/agent-zero/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"job_id\": \"$HIGH_RISK_ID\",
    \"task_id\": \"$HIGH_RISK_ID\",
    \"action\": \"execute\"
  }"
```

Expected:

- intake accepts the task
- execution returns `blocked` until review artifacts are submitted

## Deployment command

From the repo root on the target host:

```bash
docker compose up -d --build flow-postgres flow-redis bizbrain-lite openclaw hermes agent-zero postiz postiz_postgres postiz_redis portainer
```

Then inspect:

```bash
docker compose ps
docker compose logs --tail=100 bizbrain-lite
```