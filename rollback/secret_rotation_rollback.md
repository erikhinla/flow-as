# FLOW Agent AS Secret Rotation Rollback

Date: 2026-05-04
Scope: Dashboard Basic Auth credential rollback and intake API token rollback
Risk: Medium

## Preconditions

- Retrieve the prior approved secret set from your secret manager or secure operator backup.
- Do not restore secrets from repo history.
- Schedule a short maintenance window because affected containers must be recreated.

## Rollback Steps

1. Update the ignored deployment `.env` with the prior approved values for:
   - `DASHBOARD_BASIC_AUTH_USER`
   - `DASHBOARD_BASIC_AUTH_PASSWORD`
   - `OPENCLAW_API_TOKEN`
2. Recreate the affected services:

```bash
docker compose -f docker-compose.yml up -d --force-recreate flow-dashboard bizbrain-lite flow-discord-bot
```

3. Verify the control plane is healthy:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:18000/v1/health
```

4. Verify the restored credentials work and the rotated credentials no longer work.

## Validation Checklist

- Dashboard with restored credentials returns `200`.
- Dashboard with rotated credentials returns `401`.
- Intake submission with restored API token is accepted.
- Intake submission with rotated API token returns `401`.
- `GET /v1/health` returns `200`.

## If Rollback Fails

1. Confirm the `.env` values are present and non-empty.
2. Re-run `docker compose -f docker-compose.yml config` to catch env or compose syntax issues.
3. Recreate only the failing service again with `--force-recreate`.
4. If the dashboard fails, confirm the entrypoint still exits closed without the password env; if not, rebuild the dashboard image and recreate it again.

## Deferred Item

- No repo-stored copy of previous secrets is kept. This is intentional to avoid turning rollback documentation into a secret storage path.