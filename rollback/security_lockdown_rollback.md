# FLOW Agent AS Security Lockdown Rollback Plan

**Emergency Rollback Procedure**  
**Estimated Time:** 5-10 minutes  
**Risk:** Medium (Service interruption)  

## Quick Rollback Commands

### If Authentication Breaks Dashboard Access

```bash
# 1. Disable dashboard authentication quickly
docker exec flow-dashboard sed -i 's/^        auth_basic /        # auth_basic /' /etc/nginx/nginx.conf
docker exec flow-dashboard sed -i 's/^        auth_basic_user_file /        # auth_basic_user_file /' /etc/nginx/nginx.conf
docker exec flow-dashboard nginx -s reload

# 2. Verify dashboard accessibility  
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
# Should return 200
```

### If Authentication Breaks API Integration

```bash
# 1. Remove authentication requirement from intake router
docker exec bizbrain-lite sed -i 's/dependencies=\[Depends(require_api_token)\]//g' /app/app/api/openclaw_intake.py

# 2. Restart bizbrain-lite service
docker compose restart bizbrain-lite

# 3. Test unauthenticated access
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Content-Type: application/json" \
  -d '{"task_id":"rollback-test","title":"Test","goal":"Test rollback","task_type":"healthcheck","risk_tier":"low","preferred_owner":"hermes","output_required":"None","review_required":false,"status":"pending"}'
```

## Complete Rollback (Revert All Changes)

### 1. Dashboard Files

**Restore nginx.conf:**
```bash
# Remove authentication block
cat > services/dashboard/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;

        # Handle client-side routing
        location / {
            try_files $uri $uri/ /index.html;
        }

        # Proxy API requests
        location /api/ {
            proxy_pass http://bizbrain-lite:8000/v1/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
```

**Restore Dockerfile:**
```bash
# Remove runtime credential generation
sed -i '/RUN apk add --no-cache apache2-utils/d' services/dashboard/Dockerfile
sed -i '/COPY services\/dashboard\/docker-entrypoint.sh \/docker-entrypoint.sh/d' services/dashboard/Dockerfile
sed -i '/RUN chmod +x \/docker-entrypoint.sh/d' services/dashboard/Dockerfile
sed -i 's/ENTRYPOINT \["\/docker-entrypoint.sh"\]/CMD ["nginx", "-g", "daemon off;"]/' services/dashboard/Dockerfile
```

### 2. Intake Endpoint

**Restore openclaw_intake.py:**
```bash
# Remove auth import
sed -i '/from app.api.deps import require_api_token/d' services/bizbrain_lite/app/api/openclaw_intake.py

# Remove dependencies parameter
sed -i 's/, dependencies=\[Depends(require_api_token)\]//g' services/bizbrain_lite/app/api/openclaw_intake.py
```

### 3. Rebuild and Restart

```bash
# Rebuild affected services
docker compose build flow-dashboard bizbrain-lite

# Restart all services
docker compose down
docker compose up -d

# Verify rollback success
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/           # Should return 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:18000/v1/health # Should return 200
```

## Rollback Verification Tests

### Test Unauthenticated Dashboard Access
```bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/)
if [ "$RESPONSE" = "200" ]; then
    echo "✅ Rollback Success: Dashboard accessible without auth"
else
    echo "❌ Rollback Failed: Dashboard still requires auth"
fi
```

### Test Unauthenticated Task Submission
```bash
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"task_id":"rollback-test-001","created_at":"2026-05-04T23:30:00Z","source":"manual","title":"Rollback test","goal":"Verify rollback works","task_type":"healthcheck","risk_tier":"low","preferred_owner":"hermes","output_required":"None","review_required":false,"status":"pending"}' \
  -o /dev/null -w "%{http_code}" \
  http://localhost:18000/v1/intake/task)

if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "202" ]; then
    echo "✅ Rollback Success: Task submission works without auth"
else
    echo "❌ Rollback Failed: Task submission still requires auth" 
fi
```

## Emergency Contacts & Escalation

**If rollback fails or system remains inaccessible:**

1. **Container Reset:**
   ```bash
   docker compose down --volumes
    git revert <security-lockdown-commit>
   docker compose up -d
   ```

2. **Complete Environment Reset:**
   ```bash
   docker system prune -af
   docker volume prune -f
    git revert <security-lockdown-commit>
   docker compose up -d --build
   ```

## Recovery Validation

After rollback, verify:
- [ ] Dashboard accessible at http://localhost:5173 without credentials
- [ ] Task submission works without X-Api-Token header  
- [ ] All containers healthy and running
- [ ] Logs show no authentication errors
- [ ] Queue workers processing tasks normally

## Notes

- Original security vulnerabilities will be re-exposed after rollback
- Plan security re-implementation carefully if rollback is required
- Document any issues encountered during rollback for future reference
- Consider staged rollback (dashboard first, then API) if partial rollback needed