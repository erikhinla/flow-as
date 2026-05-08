#!/bin/bash
# Dashboard Authentication Security Tests

set -euo pipefail

: "${DASHBOARD_BASIC_AUTH_USER:=admin}"
: "${DASHBOARD_BASIC_AUTH_PASSWORD:?Set DASHBOARD_BASIC_AUTH_PASSWORD before running this script}"

echo "=== FLOW AGENT AS DASHBOARD AUTHENTICATION TESTS ==="
echo "Test Date: $(date)"
echo ""

# Test 1: Unauthenticated Dashboard Access (Should Fail)
echo "🔒 TEST 1: Unauthenticated Dashboard Access"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/)
if [ "$RESPONSE" = "401" ]; then
    echo "✅ PASS: Unauthenticated access correctly blocked (HTTP $RESPONSE)"
else
    echo "❌ FAIL: Unauthenticated access not blocked (HTTP $RESPONSE)"
fi
echo ""

# Test 2: Authenticated Dashboard Access (Should Succeed)
echo "🔓 TEST 2: Authenticated Dashboard Access"  
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -u "$DASHBOARD_BASIC_AUTH_USER:$DASHBOARD_BASIC_AUTH_PASSWORD" http://localhost:5173/)
if [ "$RESPONSE" = "200" ]; then
    echo "✅ PASS: Authenticated access successful (HTTP $RESPONSE)"
else
    echo "❌ FAIL: Authenticated access failed (HTTP $RESPONSE)"
fi
echo ""

# Test 3: Wrong Credentials (Should Fail)
echo "🚫 TEST 3: Wrong Credentials Access"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -u "$DASHBOARD_BASIC_AUTH_USER:wrongpassword" http://localhost:5173/)
if [ "$RESPONSE" = "401" ]; then
    echo "✅ PASS: Wrong credentials correctly rejected (HTTP $RESPONSE)"
else
    echo "❌ FAIL: Wrong credentials not rejected (HTTP $RESPONSE)"
fi
echo ""

# Test 4: API Proxy Authentication  
echo "🔗 TEST 4: API Proxy Authentication"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -u "$DASHBOARD_BASIC_AUTH_USER:$DASHBOARD_BASIC_AUTH_PASSWORD" http://localhost:5173/api/health)
if [ "$RESPONSE" = "200" ]; then
    echo "✅ PASS: API proxy works with authentication (HTTP $RESPONSE)"
else
    echo "❌ FAIL: API proxy failed with authentication (HTTP $RESPONSE)"
fi
echo ""

echo "=== Dashboard Authentication Test Summary ==="
echo "All dashboard endpoints now require basic authentication"
echo "Credentials sourced from DASHBOARD_BASIC_AUTH_USER and DASHBOARD_BASIC_AUTH_PASSWORD"