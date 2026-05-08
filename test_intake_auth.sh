#!/bin/bash
# Intake Endpoint Authentication Security Tests

set -euo pipefail

: "${OPENCLAW_API_TOKEN:=${BIZBRAIN_API_TOKEN:-}}"
: "${OPENCLAW_API_TOKEN:?Set OPENCLAW_API_TOKEN before running this script}"

echo "=== FLOW AGENT AS INTAKE ENDPOINT AUTHENTICATION TESTS ==="
echo "Test Date: $(date)"
echo ""

API_TOKEN="$OPENCLAW_API_TOKEN"
AUTHORIZED_TASK_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

# Test 1: Unauthenticated Task Submission (Should Fail)
echo "🔒 TEST 1: Unauthenticated Task Submission"
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-unauth-001",
    "created_at": "2026-05-04T23:15:00Z",
    "source": "manual",
    "title": "Unauthorized test",
    "goal": "This should be blocked",
    "task_type": "healthcheck",
    "risk_tier": "low",
    "preferred_owner": "hermes",
    "output_required": "None",
    "review_required": false,
    "status": "pending"
  }' \
  -o /dev/null -w "%{http_code}" \
  http://localhost:18000/v1/intake/task)

if [ "$RESPONSE" = "401" ]; then
    echo "✅ PASS: Unauthenticated task submission blocked (HTTP $RESPONSE)"
else
    echo "❌ FAIL: Unauthenticated task submission not blocked (HTTP $RESPONSE)"
fi
echo ""

# Test 2: Invalid API Token (Should Fail)
echo "🚫 TEST 2: Invalid API Token"
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "X-Api-Token: invalid-token-123" \
  -d '{
    "task_id": "test-invalid-001", 
    "created_at": "2026-05-04T23:15:00Z",
    "source": "manual",
    "title": "Invalid token test",
    "goal": "This should be blocked",
    "task_type": "healthcheck",
    "risk_tier": "low", 
    "preferred_owner": "hermes",
    "output_required": "None",
    "review_required": false,
    "status": "pending"
  }' \
  -o /dev/null -w "%{http_code}" \
  http://localhost:18000/v1/intake/task)

if [ "$RESPONSE" = "401" ]; then
    echo "✅ PASS: Invalid API token correctly rejected (HTTP $RESPONSE)"
else
    echo "❌ FAIL: Invalid API token not rejected (HTTP $RESPONSE)"
fi
echo ""

# Test 3: Valid API Token with Valid Task (Should Succeed)
echo "🔓 TEST 3: Valid API Token with Valid Task"
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "X-Api-Token: $API_TOKEN" \
  -d '{
    "task_id": "'"$AUTHORIZED_TASK_ID"'",
    "created_at": "2026-05-04T23:15:00Z", 
    "source": "manual",
    "title": "Security test - authorized",
    "goal": "Verify authenticated task submission works",
    "task_type": "healthcheck",
    "risk_tier": "low",
    "preferred_owner": "hermes", 
    "output_required": "Security test confirmation",
    "review_required": false,
    "status": "pending"
  }' \
  http://localhost:18000/v1/intake/task)

if printf '%s' "$RESPONSE" | grep -q '"status"[[:space:]]*:[[:space:]]*"accepted"'; then
    echo "✅ PASS: Valid API token and task accepted"
else
    echo "❌ FAIL: Valid API token and task rejected"
    echo "$RESPONSE"
fi
echo ""

# Test 4: Other Intake Endpoints (Should Require Auth)
echo "🔐 TEST 4: Other Intake Endpoints Authentication"

# Test status endpoint without auth
STATUS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:18000/v1/intake/status)
if [ "$STATUS_RESPONSE" = "401" ]; then
    echo "✅ PASS: /intake/status requires authentication (HTTP $STATUS_RESPONSE)"
else
    echo "❌ FAIL: /intake/status does not require authentication (HTTP $STATUS_RESPONSE)"
fi

# Test queues endpoint without auth  
QUEUES_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:18000/v1/intake/queues/status)
if [ "$QUEUES_RESPONSE" = "401" ]; then
    echo "✅ PASS: /intake/queues/status requires authentication (HTTP $QUEUES_RESPONSE)"
else
    echo "❌ FAIL: /intake/queues/status does not require authentication (HTTP $QUEUES_RESPONSE)"
fi
echo ""

echo "=== Intake Authentication Test Summary ==="
echo "All intake endpoints now require X-Api-Token header"
echo "API token sourced from OPENCLAW_API_TOKEN"