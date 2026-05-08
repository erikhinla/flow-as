# Hostinger VPS Deployment (FLOW Agent AS)

## 1) Prepare Ubuntu VPS

```bash
ssh root@<VPS_IP>
mkdir -p /opt/flow-as
cd /opt/flow-as
git clone https://github.com/erikhinla/flow-as.git .
bash scripts/hostinger/bootstrap_vps.sh
```

## 2) Configure environment

```bash
cp .env.example .env
nano .env
```

Required minimum values:

- `FLOW_DB_PASSWORD`
- `BIZBRAIN_API_TOKEN`
- `WEBHOOK_API_KEY`
- `OPENAI_API_KEY` (or point `OPENAI_BASE_URL` to your model gateway)

## 3) Deploy

```bash
bash scripts/hostinger/deploy.sh /opt/flow-as
```

## 4) Validate

```bash
bash scripts/hostinger/healthcheck.sh localhost
docker compose ps
docker compose logs -f --tail=100 flow-orchestrator
```

## 5) Rollback

```bash
bash scripts/hostinger/rollback.sh /opt/flow-as
```

## Port / firewall notes

- `22` SSH
- `9443` Portainer HTTPS
- `9000` Portainer HTTP
- `18000` FLOW orchestrator API
- `8080` FLOW gateway intake API
- `50090` FLOW worker gateway

Avoid exposing Postgres/Redis publicly.
