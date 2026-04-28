# FLOW Agent OS — Complete Production Infrastructure

> **System:** 6-8 specialized agents on Hostinger VPS | Mac = control/monitor only | All execution on VPS
> **Model strategy:** Mercury 2 via OpenRouter (orchestration/synthesis) · Ollama qwen2.5:3b + qwen2.5-coder:3b (cheap helpers)

---

## 1. docker-compose.yml

```yaml
# /opt/flow/docker-compose.yml
# FLOW Agent OS — Production Docker Compose
# All secrets injected from .env — never commit .env to git

version: "3.9"

x-common-agent: &common-agent
  restart: unless-stopped
  networks:
    - flow-net
  env_file:
    - /opt/flow/.env
  logging:
    driver: "json-file"
    options:
      max-size: "50m"
      max-file: "5"

services:

  # ─────────────────────────────────────────────
  # INFRASTRUCTURE
  # ─────────────────────────────────────────────

  postgres:
    image: ankane/pgvector:latest
    container_name: flow-postgres
    restart: unless-stopped
    networks:
      - flow-net
    env_file:
      - /opt/flow/.env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - /opt/flow/postgres/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  redis:
    image: redis:7.2-alpine
    container_name: flow-redis
    restart: unless-stopped
    networks:
      - flow-net
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 60 1000
      --appendonly yes
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "20m"
        max-file: "3"

  ollama:
    image: ollama/ollama:latest
    container_name: flow-ollama
    restart: unless-stopped
    networks:
      - flow-net
    volumes:
      - ollama-models:/root/.ollama
    environment:
      OLLAMA_HOST: 0.0.0.0
      OLLAMA_NUM_PARALLEL: 2
      OLLAMA_MAX_LOADED_MODELS: 2
    # GPU passthrough (uncomment if NVIDIA GPU available on VPS)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
    expose:
      - "11434"
    # NOT exposed on host — internal only. Access via gateway or direct agent calls.
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # ─────────────────────────────────────────────
  # GATEWAY (nginx reverse proxy + routing)
  # ─────────────────────────────────────────────

  gateway:
    image: nginx:alpine
    container_name: flow-gateway
    restart: unless-stopped
    networks:
      - flow-net
    ports:
      - "8080:80"
    volumes:
      - /opt/flow/gateway/nginx.conf:/etc/nginx/nginx.conf:ro
      - /opt/flow/gateway/conf.d:/etc/nginx/conf.d:ro
      - /opt/flow/gateway/html:/usr/share/nginx/html:ro
      - gateway-logs:/var/log/nginx
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  # ─────────────────────────────────────────────
  # AGENTS
  # ─────────────────────────────────────────────

  orchestrator:
    <<: *common-agent
    image: python:3.11-slim
    container_name: flow-orchestrator
    working_dir: /app
    volumes:
      - /opt/flow/agents/orchestrator:/app:ro
      - /opt/flow/shared:/shared:ro
      - agent-logs:/var/log/agents
    environment:
      AGENT_NAME: orchestrator
      AGENT_ROLE: orchestration
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8001
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8001 --workers 2 --log-level ${LOG_LEVEL}"
    expose:
      - "8001"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  executor:
    <<: *common-agent
    image: python:3.11-slim
    container_name: flow-executor
    working_dir: /app
    volumes:
      - /opt/flow/agents/executor:/app:ro
      - /opt/flow/shared:/shared:ro
      - executor-workspace:/workspace
      - agent-logs:/var/log/agents
    environment:
      AGENT_NAME: executor
      AGENT_ROLE: execution
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8002
      SANDBOX_DIR: /workspace
      EXECUTION_TIMEOUT: ${AGENT_TIMEOUT_SECONDS}
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8002 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8002"
    depends_on:
      - orchestrator
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8002/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  researcher:
    <<: *common-agent
    image: python:3.11-slim
    container_name: flow-researcher
    working_dir: /app
    volumes:
      - /opt/flow/agents/researcher:/app:ro
      - /opt/flow/shared:/shared:ro
      - agent-logs:/var/log/agents
    environment:
      AGENT_NAME: researcher
      AGENT_ROLE: research
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8003
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8003 --workers 2 --log-level ${LOG_LEVEL}"
    expose:
      - "8003"
    depends_on:
      - orchestrator
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8003/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  coder:
    <<: *common-agent
    image: python:3.11-slim
    container_name: flow-coder
    working_dir: /app
    volumes:
      - /opt/flow/agents/coder:/app:ro
      - /opt/flow/shared:/shared:ro
      - agent-logs:/var/log/agents
    environment:
      AGENT_NAME: coder
      AGENT_ROLE: coding
      MODEL_BACKEND: ollama
      MODEL_ID: ${OLLAMA_CODER_MODEL}
      PORT: 8004
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8004 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8004"
    depends_on:
      - orchestrator
      - ollama
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8004/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  critic:
    <<: *common-agent
    image: python:3.11-slim
    container_name: flow-critic
    working_dir: /app
    volumes:
      - /opt/flow/agents/critic:/app:ro
      - /opt/flow/shared:/shared:ro
      - agent-logs:/var/log/agents
    environment:
      AGENT_NAME: critic
      AGENT_ROLE: verification
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8005
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8005 --workers 2 --log-level ${LOG_LEVEL}"
    expose:
      - "8005"
    depends_on:
      - orchestrator
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8005/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  social:
    <<: *common-agent
    image: python:3.11-slim
    container_name: flow-social
    working_dir: /app
    volumes:
      - /opt/flow/agents/social:/app:ro
      - /opt/flow/shared:/shared:ro
      - agent-logs:/var/log/agents
    environment:
      AGENT_NAME: social
      AGENT_ROLE: distribution
      MODEL_BACKEND: ollama
      MODEL_ID: ${OLLAMA_HELPER_MODEL}
      PORT: 8006
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8006 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8006"
    depends_on:
      - orchestrator
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8006/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  librarian:
    <<: *common-agent
    image: python:3.11-slim
    container_name: flow-librarian
    working_dir: /app
    volumes:
      - /opt/flow/agents/librarian:/app:ro
      - /opt/flow/shared:/shared:ro
      - agent-logs:/var/log/agents
    environment:
      AGENT_NAME: librarian
      AGENT_ROLE: memory
      MODEL_BACKEND: ollama
      MODEL_ID: ${OLLAMA_HELPER_MODEL}
      PORT: 8007
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8007 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8007"
    depends_on:
      postgres:
        condition: service_healthy
      orchestrator:
        condition: service_started
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8007/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  # ─────────────────────────────────────────────
  # UI
  # ─────────────────────────────────────────────

  ui:
    image: nginx:alpine
    container_name: flow-ui
    restart: unless-stopped
    networks:
      - flow-net
    ports:
      - "3000:80"
    volumes:
      - /opt/flow/ui/dist:/usr/share/nginx/html:ro
      - /opt/flow/ui/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - gateway
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80/"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "20m"
        max-file: "3"

# ─────────────────────────────────────────────
# NETWORKS
# ─────────────────────────────────────────────

networks:
  flow-net:
    driver: bridge
    name: flow-net
    ipam:
      config:
        - subnet: 172.20.0.0/16

# ─────────────────────────────────────────────
# VOLUMES
# ─────────────────────────────────────────────

volumes:
  postgres-data:
    name: flow-postgres-data
    driver: local
  redis-data:
    name: flow-redis-data
    driver: local
  ollama-models:
    name: flow-ollama-models
    driver: local
  executor-workspace:
    name: flow-executor-workspace
    driver: local
  agent-logs:
    name: flow-agent-logs
    driver: local
  gateway-logs:
    name: flow-gateway-logs
    driver: local
```

---

## 2. .env.full

```env
# ════════════════════════════════════════════════
# FLOW Agent OS — Complete Environment Variables
# Save as: /opt/flow/.env
# chmod 600 /opt/flow/.env
# NEVER commit this file to version control
# ════════════════════════════════════════════════

# ── OpenRouter / Mercury 2 ──────────────────────
OPENROUTER_API_KEY=sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MERCURY2_MODEL=inception/mercury-2
OPENROUTER_HTTP_REFERER=https://flow-agent-os.internal
OPENROUTER_APP_TITLE=FLOW-AgentOS

# ── Ollama (local VPS) ──────────────────────────
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_CODER_MODEL=qwen2.5-coder:3b
OLLAMA_HELPER_MODEL=qwen2.5:3b
OLLAMA_REQUEST_TIMEOUT=90
OLLAMA_NUM_PARALLEL=2

# ── PostgreSQL ──────────────────────────────────
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=flowadmin
POSTGRES_PASSWORD=Fl0wPg$ecureP@ss2025!
POSTGRES_DB=flowdb
DATABASE_URL=postgresql://flowadmin:Fl0wPg$ecureP@ss2025!@postgres:5432/flowdb
PGVECTOR_DIMENSIONS=1536

# ── Redis ───────────────────────────────────────
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=Fl0wR3d1s$ecure2025!
REDIS_URL=redis://:Fl0wR3d1s$ecure2025!@redis:6379/0
REDIS_QUEUE_DB=0
REDIS_CACHE_DB=1
BULLMQ_PREFIX=flow

# ── Security ────────────────────────────────────
JWT_SECRET=c7f3a9e2b1d04f6e8a5c2b7d9e1f3a8c6b4d2e9f1c3a7b5d0e2f8a4c6b3d1e9
API_SECRET_KEY=f2d8a1c5e9b3f6a4c7d0e2b8a5c1f3e7d9b4a6c0e8f2d5b7a9c3e1f4d6b0a8
INTERNAL_API_TOKEN=IntApT0k3n$2025FlowOS!SecureInternal

# ── Agent Runtime ───────────────────────────────
AGENT_TIMEOUT_SECONDS=120
MAX_RETRIES=3
RETRY_BACKOFF_MS=1000
MAX_CONCURRENT_TASKS=10
TASK_QUEUE_NAME=flow:tasks
RESULT_TTL_SECONDS=3600

# ── Logging ─────────────────────────────────────
LOG_LEVEL=info
LOG_FORMAT=json
LOG_DIR=/var/log/agents

# ── Node / Python Environment ───────────────────
NODE_ENV=production
PYTHON_ENV=production
DEBUG=false

# ── Per-Agent: Orchestrator ─────────────────────
ORCHESTRATOR_AGENT_NAME=orchestrator
ORCHESTRATOR_AGENT_ROLE=orchestration
ORCHESTRATOR_MODEL_BACKEND=openrouter
ORCHESTRATOR_PORT=8001
ORCHESTRATOR_HOST=orchestrator
ORCHESTRATOR_MAX_SUBTASKS=8
ORCHESTRATOR_PLAN_MODEL=${MERCURY2_MODEL}

# ── Per-Agent: Executor ─────────────────────────
EXECUTOR_AGENT_NAME=executor
EXECUTOR_AGENT_ROLE=execution
EXECUTOR_MODEL_BACKEND=openrouter
EXECUTOR_PORT=8002
EXECUTOR_HOST=executor
EXECUTOR_SANDBOX_DIR=/workspace
EXECUTOR_MAX_RUNTIME_SECONDS=300
EXECUTOR_ALLOWED_COMMANDS=python,bash,node,pip,npm,curl,wget,jq

# ── Per-Agent: Researcher ───────────────────────
RESEARCHER_AGENT_NAME=researcher
RESEARCHER_AGENT_ROLE=research
RESEARCHER_MODEL_BACKEND=openrouter
RESEARCHER_PORT=8003
RESEARCHER_HOST=researcher
RESEARCHER_MAX_SOURCES=10
RESEARCHER_SYNTHESIS_MODEL=${MERCURY2_MODEL}
SEARXNG_URL=http://searxng:8888
BRAVE_API_KEY=YOUR_BRAVE_SEARCH_API_KEY_HERE

# ── Per-Agent: Coder ────────────────────────────
CODER_AGENT_NAME=coder
CODER_AGENT_ROLE=coding
CODER_MODEL_BACKEND=ollama
CODER_PORT=8004
CODER_HOST=coder
CODER_MODEL=${OLLAMA_CODER_MODEL}
CODER_MAX_TOKENS=4096
CODER_TEMPERATURE=0.1

# ── Per-Agent: Critic ───────────────────────────
CRITIC_AGENT_NAME=critic
CRITIC_AGENT_ROLE=verification
CRITIC_MODEL_BACKEND=openrouter
CRITIC_PORT=8005
CRITIC_HOST=critic
CRITIC_MODEL=${MERCURY2_MODEL}
CRITIC_STRICT_MODE=true
CRITIC_SCORE_THRESHOLD=0.75

# ── Per-Agent: Social ───────────────────────────
SOCIAL_AGENT_NAME=social
SOCIAL_AGENT_ROLE=distribution
SOCIAL_MODEL_BACKEND=ollama
SOCIAL_PORT=8006
SOCIAL_HOST=social
SOCIAL_MODEL=${OLLAMA_HELPER_MODEL}
TWITTER_API_KEY=YOUR_TWITTER_API_KEY_HERE
TWITTER_API_SECRET=YOUR_TWITTER_API_SECRET_HERE
TWITTER_ACCESS_TOKEN=YOUR_TWITTER_ACCESS_TOKEN_HERE
TWITTER_ACCESS_SECRET=YOUR_TWITTER_ACCESS_SECRET_HERE
LINKEDIN_ACCESS_TOKEN=YOUR_LINKEDIN_ACCESS_TOKEN_HERE
BUFFER_ACCESS_TOKEN=YOUR_BUFFER_ACCESS_TOKEN_HERE

# ── Per-Agent: Librarian ────────────────────────
LIBRARIAN_AGENT_NAME=librarian
LIBRARIAN_AGENT_ROLE=memory
LIBRARIAN_MODEL_BACKEND=ollama
LIBRARIAN_PORT=8007
LIBRARIAN_HOST=librarian
LIBRARIAN_MODEL=${OLLAMA_HELPER_MODEL}
LIBRARIAN_EMBEDDING_MODEL=nomic-embed-text
LIBRARIAN_VECTOR_TABLE=agent_memories
LIBRARIAN_MAX_RESULTS=20
LIBRARIAN_SIMILARITY_THRESHOLD=0.7

# ── Gateway ─────────────────────────────────────
GATEWAY_HOST=gateway
GATEWAY_PORT=8080
GATEWAY_RATE_LIMIT_RPS=100
GATEWAY_RATE_LIMIT_BURST=200
GATEWAY_TIMEOUT_SECONDS=180

# ── UI ───────────────────────────────────────────
UI_HOST=ui
UI_PORT=3000
VITE_API_BASE_URL=http://YOUR_VPS_IP:8080
VITE_WS_URL=ws://YOUR_VPS_IP:8080/ws

# ── Monitoring (optional — expand later) ────────
PROMETHEUS_ENABLED=false
GRAFANA_ENABLED=false
SENTRY_DSN=

# ── Backup ───────────────────────────────────────
BACKUP_DIR=/opt/flow/backups
BACKUP_RETENTION_DAYS=7
```

---

## 3. Portainer Stack Layout

### Stack Definitions

Portainer stacks are defined as named sub-compose files that Portainer's Stack feature can deploy independently. Store each at `/opt/flow/stacks/`.

---

### CORE Stack — `/opt/flow/stacks/core.yml`

```yaml
# Portainer Stack: CORE
# Deploy FIRST — all other stacks depend on this
# Portainer: Stacks → Add Stack → "flow-core" → paste or upload this file

version: "3.9"

services:

  postgres:
    image: ankane/pgvector:latest
    container_name: flow-postgres
    restart: unless-stopped
    networks:
      - flow-net
    env_file:
      - /opt/flow/.env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - flow-postgres-data:/var/lib/postgresql/data
      - /opt/flow/postgres/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

  redis:
    image: redis:7.2-alpine
    container_name: flow-redis
    restart: unless-stopped
    networks:
      - flow-net
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 60 1000
      --appendonly yes
    volumes:
      - flow-redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  ollama:
    image: ollama/ollama:latest
    container_name: flow-ollama
    restart: unless-stopped
    networks:
      - flow-net
    volumes:
      - flow-ollama-models:/root/.ollama
    environment:
      OLLAMA_HOST: 0.0.0.0
      OLLAMA_NUM_PARALLEL: 2
      OLLAMA_MAX_LOADED_MODELS: 2
    expose:
      - "11434"

networks:
  flow-net:
    external: true
    name: flow-net

volumes:
  flow-postgres-data:
    external: true
  flow-redis-data:
    external: true
  flow-ollama-models:
    external: true
```

---

### RUNTIME Stack — `/opt/flow/stacks/runtime.yml`

```yaml
# Portainer Stack: RUNTIME
# Deploy SECOND — depends on CORE stack being healthy
# Portainer: Stacks → Add Stack → "flow-runtime"

version: "3.9"

services:

  gateway:
    image: nginx:alpine
    container_name: flow-gateway
    restart: unless-stopped
    networks:
      - flow-net
    ports:
      - "8080:80"
    volumes:
      - /opt/flow/gateway/nginx.conf:/etc/nginx/nginx.conf:ro
      - /opt/flow/gateway/conf.d:/etc/nginx/conf.d:ro
      - /opt/flow/gateway/html:/usr/share/nginx/html:ro
      - flow-gateway-logs:/var/log/nginx
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  orchestrator:
    image: python:3.11-slim
    container_name: flow-orchestrator
    restart: unless-stopped
    networks:
      - flow-net
    working_dir: /app
    env_file:
      - /opt/flow/.env
    environment:
      AGENT_NAME: orchestrator
      AGENT_ROLE: orchestration
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8001
    volumes:
      - /opt/flow/agents/orchestrator:/app:ro
      - /opt/flow/shared:/shared:ro
      - flow-agent-logs:/var/log/agents
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8001 --workers 2 --log-level ${LOG_LEVEL}"
    expose:
      - "8001"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  librarian:
    image: python:3.11-slim
    container_name: flow-librarian
    restart: unless-stopped
    networks:
      - flow-net
    working_dir: /app
    env_file:
      - /opt/flow/.env
    environment:
      AGENT_NAME: librarian
      AGENT_ROLE: memory
      MODEL_BACKEND: ollama
      MODEL_ID: ${OLLAMA_HELPER_MODEL}
      PORT: 8007
    volumes:
      - /opt/flow/agents/librarian:/app:ro
      - /opt/flow/shared:/shared:ro
      - flow-agent-logs:/var/log/agents
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8007 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8007"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8007/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

networks:
  flow-net:
    external: true
    name: flow-net

volumes:
  flow-gateway-logs:
    external: true
  flow-agent-logs:
    external: true
```

---

### FULL Stack — `/opt/flow/stacks/full.yml`

```yaml
# Portainer Stack: FULL
# Deploy LAST — includes all agents + UI
# Portainer: Stacks → Add Stack → "flow-full"

version: "3.9"

services:

  executor:
    image: python:3.11-slim
    container_name: flow-executor
    restart: unless-stopped
    networks:
      - flow-net
    working_dir: /app
    env_file:
      - /opt/flow/.env
    environment:
      AGENT_NAME: executor
      AGENT_ROLE: execution
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8002
      SANDBOX_DIR: /workspace
    volumes:
      - /opt/flow/agents/executor:/app:ro
      - /opt/flow/shared:/shared:ro
      - flow-executor-workspace:/workspace
      - flow-agent-logs:/var/log/agents
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8002 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8002"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8002/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  researcher:
    image: python:3.11-slim
    container_name: flow-researcher
    restart: unless-stopped
    networks:
      - flow-net
    working_dir: /app
    env_file:
      - /opt/flow/.env
    environment:
      AGENT_NAME: researcher
      AGENT_ROLE: research
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8003
    volumes:
      - /opt/flow/agents/researcher:/app:ro
      - /opt/flow/shared:/shared:ro
      - flow-agent-logs:/var/log/agents
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8003 --workers 2 --log-level ${LOG_LEVEL}"
    expose:
      - "8003"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8003/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  coder:
    image: python:3.11-slim
    container_name: flow-coder
    restart: unless-stopped
    networks:
      - flow-net
    working_dir: /app
    env_file:
      - /opt/flow/.env
    environment:
      AGENT_NAME: coder
      AGENT_ROLE: coding
      MODEL_BACKEND: ollama
      MODEL_ID: ${OLLAMA_CODER_MODEL}
      PORT: 8004
    volumes:
      - /opt/flow/agents/coder:/app:ro
      - /opt/flow/shared:/shared:ro
      - flow-agent-logs:/var/log/agents
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8004 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8004"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8004/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  critic:
    image: python:3.11-slim
    container_name: flow-critic
    restart: unless-stopped
    networks:
      - flow-net
    working_dir: /app
    env_file:
      - /opt/flow/.env
    environment:
      AGENT_NAME: critic
      AGENT_ROLE: verification
      MODEL_BACKEND: openrouter
      MODEL_ID: ${MERCURY2_MODEL}
      PORT: 8005
    volumes:
      - /opt/flow/agents/critic:/app:ro
      - /opt/flow/shared:/shared:ro
      - flow-agent-logs:/var/log/agents
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8005 --workers 2 --log-level ${LOG_LEVEL}"
    expose:
      - "8005"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8005/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  social:
    image: python:3.11-slim
    container_name: flow-social
    restart: unless-stopped
    networks:
      - flow-net
    working_dir: /app
    env_file:
      - /opt/flow/.env
    environment:
      AGENT_NAME: social
      AGENT_ROLE: distribution
      MODEL_BACKEND: ollama
      MODEL_ID: ${OLLAMA_HELPER_MODEL}
      PORT: 8006
    volumes:
      - /opt/flow/agents/social:/app:ro
      - /opt/flow/shared:/shared:ro
      - flow-agent-logs:/var/log/agents
    command: >
      sh -c "pip install --no-cache-dir -r /app/requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8006 --workers 1 --log-level ${LOG_LEVEL}"
    expose:
      - "8006"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8006/health')\""]
      interval: 20s
      timeout: 10s
      retries: 3
      start_period: 30s

  ui:
    image: nginx:alpine
    container_name: flow-ui
    restart: unless-stopped
    networks:
      - flow-net
    ports:
      - "3000:80"
    volumes:
      - /opt/flow/ui/dist:/usr/share/nginx/html:ro
      - /opt/flow/ui/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80/"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

networks:
  flow-net:
    external: true
    name: flow-net

volumes:
  flow-executor-workspace:
    external: true
  flow-agent-logs:
    external: true
```

---

## 4. Volume + Bind Mount Map

### Named Volumes

| Volume Name | Driver | Purpose | Used By |
|---|---|---|---|
| `flow-postgres-data` | local | PostgreSQL data files (tables, pgvector indexes, WAL) | `postgres` |
| `flow-redis-data` | local | Redis AOF persistence + RDB snapshots | `redis` |
| `flow-ollama-models` | local | Ollama model weights (qwen2.5:3b, qwen2.5-coder:3b) | `ollama` |
| `flow-executor-workspace` | local | Sandboxed execution scratch space for Executor agent tasks | `executor` |
| `flow-agent-logs` | local | Unified log output from all agent containers | All agents |
| `flow-gateway-logs` | local | nginx access + error logs | `gateway` |

---

### Bind Mounts

| Host Path | Container Path | Mode | Container(s) | Purpose |
|---|---|---|---|---|
| `/opt/flow/.env` | (env_file reference) | ro | All containers | Shared secrets and config |
| `/opt/flow/gateway/nginx.conf` | `/etc/nginx/nginx.conf` | ro | `gateway` | Main nginx config |
| `/opt/flow/gateway/conf.d/` | `/etc/nginx/conf.d/` | ro | `gateway` | Per-upstream routing blocks |
| `/opt/flow/gateway/html/` | `/usr/share/nginx/html/` | ro | `gateway` | Static health check page + fallback |
| `/opt/flow/postgres/init/` | `/docker-entrypoint-initdb.d/` | ro | `postgres` | SQL init scripts (pgvector extension, schema) |
| `/opt/flow/agents/orchestrator/` | `/app/` | ro | `orchestrator` | Orchestrator FastAPI source code |
| `/opt/flow/agents/executor/` | `/app/` | ro | `executor` | Executor FastAPI source code |
| `/opt/flow/agents/researcher/` | `/app/` | ro | `researcher` | Researcher FastAPI source code |
| `/opt/flow/agents/coder/` | `/app/` | ro | `coder` | Coder FastAPI source code |
| `/opt/flow/agents/critic/` | `/app/` | ro | `critic` | Critic FastAPI source code |
| `/opt/flow/agents/social/` | `/app/` | ro | `social` | Social FastAPI source code |
| `/opt/flow/agents/librarian/` | `/app/` | ro | `librarian` | Librarian FastAPI source code |
| `/opt/flow/shared/` | `/shared/` | ro | All agents | Shared utilities, schemas, prompt templates |
| `/opt/flow/ui/dist/` | `/usr/share/nginx/html/` | ro | `ui` | Built Vite/React static assets |
| `/opt/flow/ui/nginx.conf` | `/etc/nginx/conf.d/default.conf` | ro | `ui` | UI nginx server block |

---

## 5. VPS Setup Commands

```bash
#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# FLOW Agent OS — VPS Setup Script
# Run as root on a fresh Ubuntu 22.04 LTS Hostinger VPS
# Usage: bash vps-setup.sh
# ════════════════════════════════════════════════════════════

set -euo pipefail
FLOW_ROOT="/opt/flow"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " FLOW Agent OS — VPS Bootstrap"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. System update ─────────────────────────────
echo "[1/8] Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  git \
  wget \
  htop \
  ufw \
  jq \
  unzip \
  software-properties-common \
  apt-transport-https

# ── 2. Install Docker CE (official method) ────────
echo "[2/8] Installing Docker CE..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

# Verify Docker installation
docker --version
docker compose version

# ── 3. Docker daemon config ───────────────────────
echo "[3/8] Configuring Docker daemon..."
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  },
  "live-restore": true
}
EOF

systemctl enable docker
systemctl restart docker

# ── 4. Create flow-net Docker network ────────────
echo "[4/8] Creating Docker network..."
docker network create \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  flow-net 2>/dev/null || echo "flow-net already exists"

# ── 5. Create named Docker volumes ────────────────
echo "[5/8] Creating Docker volumes..."
for vol in \
  flow-postgres-data \
  flow-redis-data \
  flow-ollama-models \
  flow-executor-workspace \
  flow-agent-logs \
  flow-gateway-logs; do
  docker volume create "$vol" 2>/dev/null || echo "$vol already exists"
done

# ── 6. Create /opt/flow directory structure ───────
echo "[6/8] Creating /opt/flow directory structure..."
mkdir -p \
  "${FLOW_ROOT}" \
  "${FLOW_ROOT}/gateway/conf.d" \
  "${FLOW_ROOT}/gateway/html" \
  "${FLOW_ROOT}/postgres/init" \
  "${FLOW_ROOT}/agents/orchestrator" \
  "${FLOW_ROOT}/agents/executor" \
  "${FLOW_ROOT}/agents/researcher" \
  "${FLOW_ROOT}/agents/coder" \
  "${FLOW_ROOT}/agents/critic" \
  "${FLOW_ROOT}/agents/social" \
  "${FLOW_ROOT}/agents/librarian" \
  "${FLOW_ROOT}/shared/schemas" \
  "${FLOW_ROOT}/shared/prompts" \
  "${FLOW_ROOT}/shared/utils" \
  "${FLOW_ROOT}/ui/dist" \
  "${FLOW_ROOT}/stacks" \
  "${FLOW_ROOT}/backups" \
  "${FLOW_ROOT}/logs"

# ── 7. Create nginx gateway config ────────────────
echo "[7/8] Writing gateway nginx config..."
cat > "${FLOW_ROOT}/gateway/nginx.conf" <<'NGINX_MAIN'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format json_combined escape=json
        '{'
            '"time":"$time_iso8601",'
            '"remote_addr":"$remote_addr",'
            '"method":"$request_method",'
            '"uri":"$request_uri",'
            '"status":$status,'
            '"bytes_sent":$bytes_sent,'
            '"request_time":$request_time,'
            '"upstream_addr":"$upstream_addr",'
            '"upstream_response_time":"$upstream_response_time"'
        '}';

    access_log /var/log/nginx/access.log json_combined;

    sendfile           on;
    tcp_nopush         on;
    tcp_nodelay        on;
    keepalive_timeout  65;
    types_hash_max_size 2048;
    server_tokens      off;
    client_max_body_size 64m;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    upstream orchestrator  { server orchestrator:8001; keepalive 32; }
    upstream executor      { server executor:8002; keepalive 16; }
    upstream researcher    { server researcher:8003; keepalive 16; }
    upstream coder         { server coder:8004; keepalive 16; }
    upstream critic        { server critic:8005; keepalive 16; }
    upstream social        { server social:8006; keepalive 16; }
    upstream librarian     { server librarian:8007; keepalive 16; }

    server {
        listen 80;
        server_name _;

        # Health check endpoint
        location = /health {
            access_log off;
            add_header Content-Type application/json;
            return 200 '{"status":"ok","service":"flow-gateway"}';
        }

        # API routing
        location /api/task {
            proxy_pass http://orchestrator;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Connection "";
            proxy_read_timeout 180s;
            proxy_connect_timeout 10s;
        }

        location /api/agent/orchestrator/ {
            proxy_pass http://orchestrator/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Connection "";
            proxy_read_timeout 180s;
        }

        location /api/agent/executor/ {
            proxy_pass http://executor/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Connection "";
            proxy_read_timeout 300s;
        }

        location /api/agent/researcher/ {
            proxy_pass http://researcher/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Connection "";
            proxy_read_timeout 180s;
        }

        location /api/agent/coder/ {
            proxy_pass http://coder/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Connection "";
            proxy_read_timeout 120s;
        }

        location /api/agent/critic/ {
            proxy_pass http://critic/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Connection "";
            proxy_read_timeout 180s;
        }

        location /api/agent/social/ {
            proxy_pass http://social/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Connection "";
            proxy_read_timeout 120s;
        }

        location /api/agent/librarian/ {
            proxy_pass http://librarian/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Connection "";
            proxy_read_timeout 60s;
        }

        # Static fallback
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
        }
    }
}
NGINX_MAIN

# Gateway health check static page
cat > "${FLOW_ROOT}/gateway/html/index.html" <<'HTML'
<!DOCTYPE html>
<html><head><title>FLOW Agent OS Gateway</title></head>
<body><h1>FLOW Agent OS</h1><p>Gateway is running.</p></body>
</html>
HTML

# ── 8. Postgres init SQL (pgvector + schema) ──────
cat > "${FLOW_ROOT}/postgres/init/01-init.sql" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agent_memories (
    id          BIGSERIAL PRIMARY KEY,
    agent_name  VARCHAR(64) NOT NULL,
    session_id  UUID NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(1536),
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_agent ON agent_memories(agent_name);
CREATE INDEX IF NOT EXISTS idx_memories_session ON agent_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON agent_memories
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status      VARCHAR(32) NOT NULL DEFAULT 'pending',
    payload     JSONB NOT NULL,
    result      JSONB,
    agent       VARCHAR(64),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent  ON tasks(agent);

CREATE TABLE IF NOT EXISTS agent_logs (
    id          BIGSERIAL PRIMARY KEY,
    agent_name  VARCHAR(64) NOT NULL,
    task_id     UUID,
    level       VARCHAR(16) NOT NULL,
    message     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_agent ON agent_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_logs_task  ON agent_logs(task_id);
SQL

# ── Placeholder agent requirements + main.py ─────
for AGENT in orchestrator executor researcher coder critic social librarian; do
  # requirements.txt
  cat > "${FLOW_ROOT}/agents/${AGENT}/requirements.txt" <<'REQ'
fastapi==0.111.0
uvicorn[standard]==0.29.0
httpx==0.27.0
redis==5.0.4
asyncpg==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
tenacity==8.2.3
structlog==24.1.0
REQ

  # main.py stub
  cat > "${FLOW_ROOT}/agents/${AGENT}/main.py" <<PYAPP
"""
FLOW Agent OS — ${AGENT^} Agent
Replace this stub with your production agent logic.
"""
import os
import time
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

log = structlog.get_logger()

app = FastAPI(
    title="FLOW ${AGENT^} Agent",
    version="1.0.0",
    description="FLOW Agent OS — ${AGENT^}"
)

AGENT_NAME = os.getenv("AGENT_NAME", "${AGENT}")
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "openrouter")
MODEL_ID = os.getenv("MODEL_ID", "")
START_TIME = time.time()


class TaskRequest(BaseModel):
    task_id: str
    payload: dict
    priority: int = 5


class TaskResponse(BaseModel):
    task_id: str
    agent: str
    status: str
    result: dict | None = None


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "model_backend": MODEL_BACKEND,
        "model_id": MODEL_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }


@app.post("/task", response_model=TaskResponse)
async def handle_task(req: TaskRequest):
    log.info("task_received", agent=AGENT_NAME, task_id=req.task_id)
    # TODO: implement agent logic here
    return TaskResponse(
        task_id=req.task_id,
        agent=AGENT_NAME,
        status="accepted",
        result={"message": f"{AGENT_NAME} received task {req.task_id}"}
    )


@app.get("/info")
async def info():
    return {
        "agent": AGENT_NAME,
        "role": os.getenv("AGENT_ROLE", "unknown"),
        "model_backend": MODEL_BACKEND,
        "model_id": MODEL_ID
    }
PYAPP

done

# ── UI nginx config ───────────────────────────────
cat > "${FLOW_ROOT}/ui/nginx.conf" <<'UINGINX'
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /health {
        access_log off;
        return 200 '{"status":"ok","service":"flow-ui"}';
        add_header Content-Type application/json;
    }
}
UINGINX

# Minimal UI placeholder
cat > "${FLOW_ROOT}/ui/dist/index.html" <<'UIHTML'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FLOW Agent OS</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 2rem; }
    h1 { color: #7c3aed; } .badge { background: #1e1e2e; border: 1px solid #333; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; }
  </style>
</head>
<body>
  <h1>FLOW Agent OS</h1>
  <p>Control panel UI — replace with Vite/React build output</p>
  <div class="badge">Gateway: <a href="http://localhost:8080/health" style="color:#7c3aed">http://VPS_IP:8080/health</a></div>
</body>
</html>
UIHTML

# ── Set permissions ────────────────────────────────
chmod 600 "${FLOW_ROOT}/.env" 2>/dev/null || true
chmod -R 755 "${FLOW_ROOT}"
chown -R root:root "${FLOW_ROOT}"

# ── Firewall (ufw) ─────────────────────────────────
echo "[8/8] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 8080/tcp comment 'FLOW Gateway'
ufw allow 3000/tcp comment 'FLOW UI'
# Block Ollama from external access (internal Docker only)
ufw deny 11434/tcp comment 'Ollama internal only'
ufw --force enable
ufw status verbose

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " VPS Setup COMPLETE"
echo " Next: copy /opt/flow/.env and run deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 6. Ollama Install + Model Pull Commands

```bash
#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# FLOW Agent OS — Ollama Setup
# Runs Ollama inside Docker (flow-ollama container)
# Models are persisted in flow-ollama-models Docker volume
# ════════════════════════════════════════════════════════════

set -euo pipefail

# ── Option A: Docker-based Ollama (recommended, no GPU) ──
# The flow-ollama container is already defined in docker-compose.yml
# Start it first, then pull models into it:

echo "[1/4] Starting Ollama container..."
docker compose -f /opt/flow/docker-compose.yml up -d ollama

echo "[2/4] Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
  if docker exec flow-ollama ollama list &>/dev/null; then
    echo "Ollama is ready."
    break
  fi
  echo "  Waiting... ($i/30)"
  sleep 3
done

echo "[3/4] Pulling models..."
docker exec flow-ollama ollama pull qwen2.5:3b
docker exec flow-ollama ollama pull qwen2.5-coder:3b

# Optional: pull embedding model for Librarian agent
docker exec flow-ollama ollama pull nomic-embed-text

echo "[4/4] Verifying models..."
docker exec flow-ollama ollama list

# ── Option B: Bare-metal Ollama (for GPU passthrough) ────
# Use this if you have a GPU on the VPS and want direct GPU access
# (Comment out Option A above, use this instead)
# ─────────────────────────────────────────────────────────
# curl -fsSL https://ollama.ai/install.sh | sh
#
# # Configure Ollama to listen on all interfaces (for Docker access)
# mkdir -p /etc/systemd/system/ollama.service.d
# cat > /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0:11434"
# Environment="OLLAMA_NUM_PARALLEL=2"
# Environment="OLLAMA_MAX_LOADED_MODELS=2"
# EOF
#
# systemctl daemon-reload
# systemctl enable ollama
# systemctl start ollama
#
# # Wait for Ollama
# sleep 5
# ollama pull qwen2.5:3b
# ollama pull qwen2.5-coder:3b
# ollama pull nomic-embed-text
#
# # Verify
# ollama list
#
# # If using bare-metal Ollama, update .env:
# # OLLAMA_BASE_URL=http://host-gateway:11434
# # And add to docker-compose.yml under networks section:
# # extra_hosts:
# #   - "host-gateway:host-gateway"
# ─────────────────────────────────────────────────────────

# ── Model verification ────────────────────────────
echo ""
echo "━━━━ Model List ━━━━"
curl -s http://localhost:11434/api/tags | jq '.models[] | {name, size: .size}'

# ── Ollama service management ─────────────────────
# (for bare-metal install)
# systemctl status ollama      # check status
# systemctl restart ollama     # restart
# systemctl stop ollama        # stop
# journalctl -u ollama -f      # follow logs

# (for Docker install)
# docker logs -f flow-ollama               # follow logs
# docker exec flow-ollama ollama list      # list models
# docker restart flow-ollama               # restart container
# docker exec -it flow-ollama ollama run qwen2.5:3b  # interactive test

# ── Test model inference ──────────────────────────
echo ""
echo "━━━━ Testing qwen2.5:3b ━━━━"
curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:3b",
    "prompt": "Respond with exactly: FLOW_OK",
    "stream": false,
    "options": {"temperature": 0.0}
  }' | jq -r '.response'

echo ""
echo "━━━━ Testing qwen2.5-coder:3b ━━━━"
curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:3b",
    "prompt": "Write a python one-liner that prints hello world",
    "stream": false,
    "options": {"temperature": 0.1}
  }' | jq -r '.response'

echo ""
echo "Ollama setup complete."
```

---

## 7. Smoke Test Commands

```bash
#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# FLOW Agent OS — Smoke Tests
# Run from VPS or Mac (replace VPS_IP with actual IP)
# ════════════════════════════════════════════════════════════

VPS_IP="${VPS_IP:-localhost}"
GATEWAY="http://${VPS_IP}:8080"
UI="http://${VPS_IP}:3000"
OLLAMA="http://localhost:11434"  # internal only — run from VPS
REDIS_PASSWORD="Fl0wR3d1s$ecure2025!"  # from .env

set -euo pipefail
PASS=0; FAIL=0

run_test() {
  local name="$1"; local cmd="$2"
  echo -n "  [TEST] ${name}... "
  if eval "$cmd" &>/dev/null; then
    echo "PASS"; ((PASS++))
  else
    echo "FAIL"; ((FAIL++))
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " FLOW Agent OS Smoke Tests"
echo " Target: ${VPS_IP}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Gateway health ─────────────────────────────
echo ""
echo "── Gateway ──────────────────────────────────"
echo -n "  [TEST] GET /health... "
HEALTH=$(curl -sf "${GATEWAY}/health")
echo "$HEALTH"
echo "$HEALTH" | jq -e '.status == "ok"' > /dev/null && ((PASS++)) || ((FAIL++))

# ── 2. Postgres connection ────────────────────────
echo ""
echo "── PostgreSQL ───────────────────────────────"
run_test "Postgres container running" \
  "docker exec flow-postgres pg_isready -U flowadmin -d flowdb"

run_test "pgvector extension loaded" \
  "docker exec flow-postgres psql -U flowadmin -d flowdb -c 'SELECT extname FROM pg_extension WHERE extname=\'vector\';' | grep -q vector"

# ── 3. Redis ping ─────────────────────────────────
echo ""
echo "── Redis ────────────────────────────────────"
run_test "Redis PING" \
  "docker exec flow-redis redis-cli -a '${REDIS_PASSWORD}' ping | grep -q PONG"

run_test "Redis write/read" \
  "docker exec flow-redis redis-cli -a '${REDIS_PASSWORD}' SET flow_test OK && \
   docker exec flow-redis redis-cli -a '${REDIS_PASSWORD}' GET flow_test | grep -q OK"

# ── 4. Ollama model list ──────────────────────────
echo ""
echo "── Ollama ───────────────────────────────────"
echo -n "  [TEST] GET /api/tags... "
OLLAMA_TAGS=$(curl -sf "${OLLAMA}/api/tags" 2>/dev/null || \
              docker exec flow-ollama curl -sf http://localhost:11434/api/tags)
echo "$OLLAMA_TAGS" | jq '.models[].name'
echo "$OLLAMA_TAGS" | jq -e '.models | length > 0' > /dev/null && ((PASS++)) || ((FAIL++))

run_test "qwen2.5:3b loaded" \
  "docker exec flow-ollama ollama list | grep -q 'qwen2.5:3b'"

run_test "qwen2.5-coder:3b loaded" \
  "docker exec flow-ollama ollama list | grep -q 'qwen2.5-coder:3b'"

# ── 5. Agent health endpoints ─────────────────────
echo ""
echo "── Agent Health Checks ──────────────────────"
AGENTS=("orchestrator:8001" "executor:8002" "researcher:8003" "coder:8004" "critic:8005" "social:8006" "librarian:8007")
for AGENT_PORT in "${AGENTS[@]}"; do
  AGENT="${AGENT_PORT%%:*}"
  PORT="${AGENT_PORT##*:}"
  run_test "flow-${AGENT} /health" \
    "docker exec flow-${AGENT} python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')\" 2>/dev/null || \
     curl -sf ${GATEWAY}/api/agent/${AGENT}/health"
done

# ── 6. Gateway routing ────────────────────────────
echo ""
echo "── Gateway Routing ──────────────────────────"
run_test "Gateway → orchestrator" \
  "curl -sf ${GATEWAY}/api/agent/orchestrator/health | jq -e '.status == \"ok\"'"

# ── 7. End-to-end task: POST /api/task ────────────
echo ""
echo "── End-to-End Task ──────────────────────────"
echo -n "  [TEST] POST /api/task {echo hello}... "
TASK_RESP=$(curl -sf -X POST "${GATEWAY}/api/task" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "smoke-test-001",
    "payload": {
      "type": "echo",
      "command": "echo hello",
      "input": "hello"
    },
    "priority": 1
  }')
echo "$TASK_RESP" | jq .
echo "$TASK_RESP" | jq -e '.status' > /dev/null && ((PASS++)) || ((FAIL++))

# ── 8. UI reachability ────────────────────────────
echo ""
echo "── UI ───────────────────────────────────────"
run_test "UI responds on :3000" \
  "curl -sf ${UI}/ | grep -q 'FLOW'"

# ── Summary ───────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " RESULTS: ${PASS} passed, ${FAIL} failed"
if [[ $FAIL -eq 0 ]]; then
  echo " ALL TESTS PASSED — system is healthy"
else
  echo " ${FAIL} TESTS FAILED — check logs:"
  echo "   docker compose -f /opt/flow/docker-compose.yml logs --tail=50"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 8. Deployment Order

```bash
#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# FLOW Agent OS — Numbered Deployment Steps
# Run each block in order on the VPS as root
# ════════════════════════════════════════════════════════════

FLOW_ROOT="/opt/flow"

# ── STEP 1: VPS Setup ─────────────────────────────
# Run the full VPS setup script (Section 5)
bash "${FLOW_ROOT}/vps-setup.sh"
# Verify Docker is running:
systemctl status docker
docker --version
docker compose version

# ── STEP 2: Install .env ──────────────────────────
# Copy your completed .env to the VPS (from Mac):
#   scp /path/to/.env.full root@YOUR_VPS_IP:/opt/flow/.env
# Then on VPS:
chmod 600 "${FLOW_ROOT}/.env"
# Quick sanity check — confirm key vars are set:
grep -E "^OPENROUTER_API_KEY|^POSTGRES_PASSWORD|^REDIS_PASSWORD|^JWT_SECRET" "${FLOW_ROOT}/.env"

# ── STEP 3: Deploy CORE Stack ─────────────────────
echo "[STEP 3] Deploying CORE stack (postgres, redis, ollama)..."
docker compose \
  -f "${FLOW_ROOT}/stacks/core.yml" \
  --env-file "${FLOW_ROOT}/.env" \
  up -d postgres redis ollama

# Wait for postgres and redis to be healthy
echo "Waiting for postgres..."
until docker exec flow-postgres pg_isready -U flowadmin -d flowdb &>/dev/null; do
  sleep 3; echo -n "."; done; echo ""

echo "Waiting for redis..."
until docker exec flow-redis redis-cli -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; do
  sleep 2; echo -n "."; done; echo ""

echo "CORE stack healthy."

# ── STEP 4: Pull Ollama Models ────────────────────
echo "[STEP 4] Pulling Ollama models..."
docker exec flow-ollama ollama pull qwen2.5:3b
docker exec flow-ollama ollama pull qwen2.5-coder:3b
docker exec flow-ollama ollama pull nomic-embed-text
echo "Models pulled:"
docker exec flow-ollama ollama list

# ── STEP 5: Deploy RUNTIME Stack ─────────────────
echo "[STEP 5] Deploying RUNTIME stack (gateway, orchestrator, librarian)..."
docker compose \
  -f "${FLOW_ROOT}/stacks/runtime.yml" \
  --env-file "${FLOW_ROOT}/.env" \
  up -d gateway orchestrator librarian

# Wait for gateway
echo "Waiting for gateway..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8080/health &>/dev/null; then
    echo "Gateway healthy."; break
  fi
  sleep 3; echo -n "."; done; echo ""

# Wait for orchestrator
echo "Waiting for orchestrator..."
for i in $(seq 1 20); do
  if docker exec flow-orchestrator \
       python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" &>/dev/null; then
    echo "Orchestrator healthy."; break
  fi
  sleep 3; echo -n "."; done; echo ""

# ── STEP 6: Deploy FULL Stack ─────────────────────
echo "[STEP 6] Deploying FULL stack (all agents + UI)..."
docker compose \
  -f "${FLOW_ROOT}/stacks/full.yml" \
  --env-file "${FLOW_ROOT}/.env" \
  up -d executor researcher coder critic social ui

# Wait for all agents
AGENTS=("executor:8002" "researcher:8003" "coder:8004" "critic:8005" "social:8006")
for AGENT_PORT in "${AGENTS[@]}"; do
  AGENT="${AGENT_PORT%%:*}"
  PORT="${AGENT_PORT##*:}"
  echo -n "Waiting for flow-${AGENT}..."
  for i in $(seq 1 20); do
    if docker exec "flow-${AGENT}" \
         python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" &>/dev/null; then
      echo " ready."; break
    fi
    sleep 3; echo -n "."; done
done

# ── STEP 7: Verify All Containers Running ─────────
echo ""
echo "[STEP 7] Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
  | grep -E "flow-|NAME"

echo ""
echo "Container count:"
docker ps --filter "name=flow-" --format "{{.Names}}" | wc -l
echo "Expected: 11 containers (2 infra + 1 ollama + 1 gateway + 7 agents + 1 ui)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Deployment complete. Run smoke tests:"
echo "   bash /opt/flow/smoke-test.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 9. Rollback Procedure

```bash
#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# FLOW Agent OS — Rollback Procedures
# Run on VPS as root
# ════════════════════════════════════════════════════════════

FLOW_ROOT="/opt/flow"
BACKUP_DIR="${FLOW_ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ════════════════════════════════════════════════
# A. POSTGRES BACKUP (always run before any rollback)
# ════════════════════════════════════════════════
backup_postgres() {
  echo "[BACKUP] Dumping Postgres to ${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz"
  mkdir -p "${BACKUP_DIR}"
  docker exec flow-postgres pg_dump \
    -U flowadmin \
    -d flowdb \
    --format=custom \
    --compress=9 \
    | gzip > "${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz"
  echo "[BACKUP] Postgres backup saved: ${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz"
  ls -lh "${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz"
}

# Run backup before anything else
backup_postgres

# ════════════════════════════════════════════════
# B. ROLL BACK A SINGLE AGENT CONTAINER
# ════════════════════════════════════════════════
rollback_single_agent() {
  local AGENT="${1}"         # e.g. orchestrator
  local PREV_TAG="${2}"      # e.g. python:3.11-slim (or a custom image tag)

  echo "[ROLLBACK] Rolling back flow-${AGENT} to image: ${PREV_TAG}"

  # Stop and remove current container
  docker stop "flow-${AGENT}" 2>/dev/null || true
  docker rm "flow-${AGENT}"   2>/dev/null || true

  # Redeploy with previous image
  # If using docker compose: update compose file image tag first, then:
  docker compose \
    -f "${FLOW_ROOT}/docker-compose.yml" \
    --env-file "${FLOW_ROOT}/.env" \
    up -d "${AGENT}"

  echo "[ROLLBACK] flow-${AGENT} restarted. Checking health..."
  sleep 10
  docker inspect --format='{{.State.Health.Status}}' "flow-${AGENT}" 2>/dev/null || \
    docker ps --filter "name=flow-${AGENT}" --format "{{.Status}}"
}

# Usage: rollback_single_agent orchestrator python:3.11-slim
# rollback_single_agent orchestrator python:3.11-slim

# ════════════════════════════════════════════════
# C. ROLL BACK ENTIRE STACK
# ════════════════════════════════════════════════
rollback_full_stack() {
  local COMPOSE_BACKUP="${1:-}"  # path to previous docker-compose.yml

  echo "[ROLLBACK] Rolling back entire FLOW stack..."

  # 1. Bring down all FLOW containers
  docker compose \
    -f "${FLOW_ROOT}/docker-compose.yml" \
    --env-file "${FLOW_ROOT}/.env" \
    down --remove-orphans

  # 2. If a previous compose file is provided, use it
  if [[ -n "${COMPOSE_BACKUP}" && -f "${COMPOSE_BACKUP}" ]]; then
    echo "[ROLLBACK] Using previous compose file: ${COMPOSE_BACKUP}"
    cp "${COMPOSE_BACKUP}" "${FLOW_ROOT}/docker-compose.yml"
  fi

  # 3. Bring stack back up in order
  docker compose \
    -f "${FLOW_ROOT}/docker-compose.yml" \
    --env-file "${FLOW_ROOT}/.env" \
    up -d postgres redis ollama

  sleep 15  # wait for infra

  docker compose \
    -f "${FLOW_ROOT}/docker-compose.yml" \
    --env-file "${FLOW_ROOT}/.env" \
    up -d gateway orchestrator librarian

  sleep 15  # wait for runtime

  docker compose \
    -f "${FLOW_ROOT}/docker-compose.yml" \
    --env-file "${FLOW_ROOT}/.env" \
    up -d executor researcher coder critic social ui

  echo "[ROLLBACK] Full stack rollback complete."
  docker ps --filter "name=flow-" --format "table {{.Names}}\t{{.Status}}"
}

# Usage: rollback_full_stack /opt/flow/backups/docker-compose.yml.bak

# ════════════════════════════════════════════════
# D. EMERGENCY: STOP ALL CONTAINERS
# ════════════════════════════════════════════════
emergency_stop() {
  echo "[EMERGENCY] Stopping all FLOW containers..."
  docker compose \
    -f "${FLOW_ROOT}/docker-compose.yml" \
    --env-file "${FLOW_ROOT}/.env" \
    down

  # Force-stop any stragglers
  docker ps --filter "name=flow-" -q | xargs -r docker stop

  echo "[EMERGENCY] All FLOW containers stopped."
  docker ps --filter "name=flow-"
}

# Usage: emergency_stop

# ════════════════════════════════════════════════
# E. REDIS FLUSH (corrupt state recovery)
# ════════════════════════════════════════════════
redis_flush_queues() {
  # Flush only BullMQ task queues (DB 0), preserve cache (DB 1)
  echo "[REDIS] Flushing BullMQ task queues (DB 0)..."
  docker exec flow-redis redis-cli \
    -a "${REDIS_PASSWORD}" \
    -n 0 \
    FLUSHDB ASYNC
  echo "[REDIS] DB 0 flushed."

  # Verify
  docker exec flow-redis redis-cli \
    -a "${REDIS_PASSWORD}" \
    -n 0 \
    DBSIZE
}

redis_flush_all() {
  echo "[REDIS] WARNING: Flushing ALL Redis data..."
  read -rp "Type 'yes' to confirm full Redis flush: " CONFIRM
  if [[ "${CONFIRM}" == "yes" ]]; then
    docker exec flow-redis redis-cli \
      -a "${REDIS_PASSWORD}" \
      FLUSHALL ASYNC
    echo "[REDIS] All Redis data flushed."
  else
    echo "[REDIS] Flush cancelled."
  fi
}

# ════════════════════════════════════════════════
# F. RESTORE POSTGRES FROM BACKUP
# ════════════════════════════════════════════════
restore_postgres() {
  local BACKUP_FILE="${1}"  # e.g. /opt/flow/backups/pg_20250101_120000.sql.gz

  if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "[ERROR] Backup file not found: ${BACKUP_FILE}"
    exit 1
  fi

  echo "[RESTORE] Restoring Postgres from ${BACKUP_FILE}..."

  # Drop and recreate database
  docker exec flow-postgres psql -U flowadmin -c "DROP DATABASE IF EXISTS flowdb;"
  docker exec flow-postgres psql -U flowadmin -c "CREATE DATABASE flowdb;"

  # Restore
  gunzip -c "${BACKUP_FILE}" | docker exec -i flow-postgres pg_restore \
    -U flowadmin \
    -d flowdb \
    --verbose \
    --no-owner \
    --no-privileges

  echo "[RESTORE] Postgres restore complete."
  docker exec flow-postgres psql -U flowadmin -d flowdb -c "\dt"
}

# Usage: restore_postgres /opt/flow/backups/pg_20250101_120000.sql.gz

# ════════════════════════════════════════════════
# QUICK REFERENCE
# ════════════════════════════════════════════════
# backup_postgres
# rollback_single_agent orchestrator python:3.11-slim
# rollback_full_stack
# emergency_stop
# redis_flush_queues
# redis_flush_all
# restore_postgres /opt/flow/backups/pg_TIMESTAMP.sql.gz
#
# View logs after rollback:
# docker compose -f /opt/flow/docker-compose.yml logs --tail=100 -f
# docker logs --tail=100 -f flow-orchestrator
```

---

## Appendix: Agent requirements.txt (shared baseline)

All agents share this base. Extend per-agent as needed:

```text
# /opt/flow/agents/<agent>/requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
httpx==0.27.0
redis==5.0.4
asyncpg==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
tenacity==8.2.3
structlog==24.1.0
python-dotenv==1.0.1
aiohttp==3.9.5

# Librarian only:
# pgvector==0.2.5
# sentence-transformers==3.0.1

# Researcher only:
# beautifulsoup4==4.12.3
# playwright==1.44.0
# lxml==5.2.2

# Executor only:
# docker==7.1.0
# paramiko==3.4.0
```

---

## Appendix: Shared Prompt Templates — `/opt/flow/shared/prompts/`

```bash
# Create shared prompt templates
mkdir -p /opt/flow/shared/prompts

cat > /opt/flow/shared/prompts/orchestrator_system.txt <<'EOF'
You are the FLOW Orchestrator. Your job is to:
1. Analyze incoming tasks and decompose them into subtasks
2. Route subtasks to the correct specialist agent
3. Track task state via Redis BullMQ queues
4. Aggregate results and return a unified response

Available agents: executor, researcher, coder, critic, social, librarian
Route coding tasks to coder, research to researcher, verification to critic.
Always persist results via librarian. Use Mercury 2 for synthesis.
EOF

cat > /opt/flow/shared/prompts/critic_system.txt <<'EOF'
You are the FLOW Critic/Verifier. Your job is to:
1. Validate outputs from other agents for correctness and quality
2. Score responses on a 0.0-1.0 scale
3. Flag hallucinations, errors, or policy violations
4. Return structured validation results with specific issues listed

Score threshold for acceptance: 0.75. Below this, return the task for revision.
EOF

cat > /opt/flow/shared/prompts/researcher_system.txt <<'EOF'
You are the FLOW Researcher. Your job is to:
1. Search the web and gather information from multiple sources
2. Synthesize findings into structured, cited summaries
3. Use Mercury 2 for synthesis of gathered data
4. Return results with source URLs and confidence scores

Always cross-reference at least 2 sources. Prioritize recency.
EOF
```

---

## File Locations Summary

| File | VPS Path |
|---|---|
| docker-compose.yml | `/opt/flow/docker-compose.yml` |
| .env | `/opt/flow/.env` |
| CORE stack | `/opt/flow/stacks/core.yml` |
| RUNTIME stack | `/opt/flow/stacks/runtime.yml` |
| FULL stack | `/opt/flow/stacks/full.yml` |
| VPS setup script | `/opt/flow/vps-setup.sh` |
| Ollama setup script | `/opt/flow/ollama-setup.sh` |
| Smoke test script | `/opt/flow/smoke-test.sh` |
| Gateway nginx config | `/opt/flow/gateway/nginx.conf` |
| Postgres init SQL | `/opt/flow/postgres/init/01-init.sql` |
| Agent source (each) | `/opt/flow/agents/<name>/` |
| Shared utilities | `/opt/flow/shared/` |
| UI dist build | `/opt/flow/ui/dist/` |
| Backups | `/opt/flow/backups/` |
