#!/bin/bash
# flow-ask-hermes.sh - Primary FLOW operator interface to Hermes Agent
# Usage: ./flow-ask-hermes.sh "Your question about FLOW system"

set -euo pipefail

QUERY="$1"
TIMEOUT="${2:-30}"  # 30 second default timeout

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [ -z "$QUERY" ]; then
    echo -e "${BLUE}FLOW Hermes Operator Interface${NC}"
    echo ""
    echo "Usage: $0 \"Your question\" [timeout_seconds]"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo "  $0 \"What tasks failed in the last hour?\""  
    echo "  $0 \"Create a task to analyze database performance\" 60"
    echo "  $0 \"Explain why the system is running slow\""
    echo "  $0 \"Show me the queue status and performance metrics\""
    echo ""
    echo -e "${YELLOW}Available data scope:${NC}"
    echo "  • Task history and outcomes"
    echo "  • System logs and metrics"
    echo "  • Performance reports"
    echo "  • Configuration schemas"
    echo "  • Runtime artifacts"
    echo ""
    echo -e "${YELLOW}Security note:${NC} All interactions are logged for audit purposes."
    echo ""
    exit 1
fi

# Validate Hermes container is running
if ! docker ps --format '{{.Names}}' | grep -q '^hermes$'; then
    echo -e "${RED}ERROR: Hermes container not running.${NC}"
    echo ""
    echo "Start Hermes operator interface with:"
    echo "  docker compose --profile operator up -d hermes"
    echo ""
    echo "Check container status:"
    echo "  docker ps | grep hermes"
    exit 1
fi

# Validate required environment variables are set
if ! docker exec hermes printenv OPENROUTER_API_KEY >/dev/null 2>&1; then
    echo -e "${RED}ERROR: OPENROUTER_API_KEY not configured in Hermes container.${NC}"
    echo ""
    echo "Set the API key in your environment and restart Hermes:"
    echo "  export OPENROUTER_API_KEY=your_key_here"
    echo "  docker compose --profile operator up -d hermes"
    exit 1
fi

# Execute query with timeout and audit logging
echo -e "${BLUE}FLOW System Intelligence Query${NC}"
echo -e "${YELLOW}Query:${NC} $QUERY"
echo -e "${YELLOW}Timestamp:${NC} $(date -Iseconds)"
echo -e "${YELLOW}Timeout:${NC} ${TIMEOUT}s"
echo "---"

# Execute Hermes query with proper error handling
if timeout "$TIMEOUT" docker exec hermes hermes chat \
    -q "$QUERY" \
    -Q \
    --source operator \
    --toolsets "file,memory,clarify,skills" 2>&1; then
    
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi

echo ""
echo "---"
echo -e "${YELLOW}Query completed:${NC} $(date -Iseconds)"

if [ $EXIT_CODE -eq 124 ]; then
    echo -e "${RED}ERROR: Query timed out after $TIMEOUT seconds${NC}"
    echo "Try a simpler question or increase timeout with:"
    echo "  $0 \"$QUERY\" $((TIMEOUT * 2))"
    exit 1
elif [ $EXIT_CODE -ne 0 ]; then
    echo -e "${RED}ERROR: Query failed with exit code $EXIT_CODE${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check Hermes container logs: docker logs hermes --tail=20"
    echo "2. Verify API key configuration"
    echo "3. Test basic connectivity: docker exec hermes hermes chat -q \"Hello\" -Q"
    exit $EXIT_CODE
fi

echo -e "${GREEN}Audit:${NC} All interactions logged in Hermes session history"
echo -e "${YELLOW}Session data:${NC} docker exec hermes ls -la /root/.hermes/sessions/"