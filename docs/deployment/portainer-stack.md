# Portainer Stack Deployment

Use this repository directly as a Portainer stack source.

## Stack config

- **Repository URL**: `https://github.com/erikhinla/flow-as.git`
- **Compose path**: `docker-compose.yml`
- **Additional file (optional)**: `docker-compose.prod.yml`
- **Environment variables**: add from `.env.example` in Portainer UI

## Recommended Portainer flow

1. Portainer → **Stacks** → **Add stack**.
2. Choose **Repository** method.
3. Set repo URL and branch.
4. Paste environment values (never commit secrets).
5. Deploy stack.

## Post-deploy checks

```bash
docker compose ps
docker compose logs --tail=100 flow-orchestrator
curl -fsS http://<VPS_IP>:18000/v1/health
curl -fsS http://<VPS_IP>:8080/health
```

## Rollback in Portainer

- Re-deploy previous commit SHA/tag in stack settings; or
- CLI fallback:

```bash
cd /opt/flow-as
git reset --hard <known_good_commit>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
