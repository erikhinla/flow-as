# FLOW dashboard Traefik route (Hostinger)

## Live temporary hostname

`https://flow.srv1863070.hstgr.cloud/`

Labels on `flow-dashboard` (also in root `docker-compose.yml`):

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.flow-dashboard.rule=Host(`flow.srv1863070.hstgr.cloud`)
  - traefik.http.routers.flow-dashboard.entrypoints=websecure
  - traefik.http.routers.flow-dashboard.tls=true
  - traefik.http.routers.flow-dashboard.tls.certresolver=letsencrypt
  - traefik.http.services.flow-dashboard.loadbalancer.server.port=80
```

## Custom hostname (pending DNS)

| Type | Name | Value |
|------|------|--------|
| A | `flow` | `2.25.90.191` |

When DNS resolves, add a second router or expand the Host rule to include:

`Host(\`flow.srv1863070.hstgr.cloud\`) || Host(\`flow.transformby10x.ai\`)`

Do not remove the temporary hostname until TLS + login succeed on the custom host.

## Acceptance checks

- Unauthenticated HTTPS → `401`
- Authenticated HTTPS → dashboard `200`
- FLOW stack remains healthy
- Postgres/Redis not published publicly
