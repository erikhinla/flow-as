# Flow Agent OS + Postiz Deployment Guide

## Hostinger VPS Setup

### Prerequisites
- Hostinger VPS with Ubuntu 22.04+ or CentOS 8+
- SSH access as root
- ~4GB RAM minimum, ~20GB disk

### Step 1: Bootstrap the VPS

```bash
ssh root@<YOUR_VPS_IP>

# One-command setup: installs Docker, configures firewall, starts Portainer
bash <(curl -fsSL https://raw.githubusercontent.com/erikhinla/flow-agent-os/main/scripts/bootstrap.sh)
```

This will:
- Install Docker & Docker Compose
- Set up UFW firewall (ports 9000, 9443, 18789, 50080, 50090, 5000)
- Create `/opt/flow-agents` directory
- Start Portainer on port 9443

### Step 2: Configure Environment Variables

```bash
nano /opt/flow-agents/.env
```

Copy from `.env.example` and fill in:

**Required for all services:**
```
OPENAI_API_KEY=sk-xxx
A0_AUTH_PASSWORD=your_password
FLOW_DB_PASSWORD=your_flow_db_password
BIZBRAIN_API_TOKEN=your_bizbrain_api_token
```

**For Postiz specifically:**
```
POSTIZ_JWT_SECRET=<generate: openssl rand -base64 32>
POSTIZ_DB_PASSWORD=<generate: openssl rand -base64 16>
POSTIZ_DOMAIN=your-vps-ip.com:5000
```

### Step 3: Deploy Everything

```bash
cd /opt/flow-agents
docker compose up -d --build
```

Wait ~2 minutes for all services to start.

### Step 4: Verify Services

```bash
docker compose ps
```

All containers should be in `Up` state.

## Service URLs

| Service | URL | Login |
|---------|-----|-------|
| **Portainer** (Dashboard) | https://<VPS_IP>:9443 | admin / password |
| **BizBrain Lite** (FLOW Control Plane) | http://<VPS_IP>:18000/docs | x-api-token for protected endpoints |
| **Postiz** (Social Media) | http://<VPS_IP>:5000 | Create first account |
| **OpenClaw** (Orchestrator) | http://<VPS_IP>:18789 | (API only) |
| **AgentZero** (Executor) | http://<VPS_IP>:50080 | Admin / A0_AUTH_PASSWORD |
| **Hermes** (Specialist) | http://<VPS_IP>:50090 | (API only) |

## Firewall Configuration

UFW is automatically configured to allow:
- **Port 9443** — Portainer HTTPS
- **Port 18000** — BizBrain Lite control plane
- **Port 9000** — Portainer HTTP redirect
- **Port 18789** — OpenClaw API
- **Port 50080** — AgentZero Web UI
- **Port 50090** — Hermes API
- **Port 5000** — Postiz Web UI
- **Port 22** — SSH (locked to your IP)

If you need to adjust:

```bash
sudo ufw allow 5000
sudo ufw reload
```

## First-Time Postiz Setup

1. Navigate to http://<VPS_IP>:5000
2. Create your first account (become admin automatically)
3. Connect social media providers (X, LinkedIn, Instagram, TikTok, etc.)
4. Set `POSTIZ_DISABLE_REGISTRATION=true` in `.env` to lock down registrations

```bash
nano /opt/flow-agents/.env
# Edit POSTIZ_DISABLE_REGISTRATION=true
docker compose restart postiz
```

## Database Backups

Postiz uses PostgreSQL. Backup the database:

```bash
docker exec postiz-postgres pg_dump -U postiz-user postiz-db > postiz-backup-$(date +%Y%m%d).sql
```

Restore:

```bash
docker exec -i postiz-postgres psql -U postiz-user postiz-db < postiz-backup-20240330.sql
```

## Troubleshooting

### Postiz not starting
```bash
docker logs postiz
docker logs postiz-postgres
docker logs postiz-redis
```

Check `.env` — ensure `POSTIZ_JWT_SECRET` and `POSTIZ_DB_PASSWORD` are set.

### Agents not connecting
```bash
docker logs openclaw
docker logs agent-zero
docker logs hermes
```

Verify LLM API keys are set in `.env`.

### Disk space full
```bash
docker system df
docker system prune -a  # WARNING: removes unused images
```

### Port already in use
```bash
lsof -i :5000  # Check what's using port 5000
# Kill if needed: kill -9 <PID>
```

## Updates

Pull latest images:

```bash
cd /opt/flow-agents
docker compose pull
docker compose up -d
```

## Logs

View all service logs:
```bash
docker compose logs -f
```

Specific service:
```bash
docker compose logs -f postiz
```

Last 100 lines:
```bash
docker compose logs --tail=100 postiz
```
