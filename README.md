# FLOW Agent OS

FLOW Agent OS is a multi-agent orchestration platform built on FastAPI, Docker Compose, PostgreSQL, Redis, and Ollama (or OpenAI/OpenRouter as model backends).

## Repository structure

| Path | Description |
|---|---|
| `api/` | Vercel serverless entrypoint |
| `services/bizbrain_lite/` | FLOW control plane (FastAPI + Postgres + Redis) |
| `intake-webhook/` | Lead-capture / diagnostic FastAPI service |
| `config/` | Hermes and other service configs |
| `scripts/` | VPS bootstrap and deploy helpers |
| `docker-compose.yml` | Full local/VPS stack |

## Local development (Docker Compose)

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full VPS setup guide.

```bash
cp .env.example .env      # fill in your secrets
docker compose up -d --build
```

---

## Deploy to Vercel

The `api/index.py` file is a minimal FastAPI application that acts as the Vercel serverless entrypoint. It exposes:

- `GET /` — index page confirming the deployment is live
- `GET /healthz` — health-check that reports whether key environment variables are configured (no secret values are exposed)

### Prerequisites

- A [Vercel](https://vercel.com) account
- The repository forked / accessible in your GitHub account

### Step-by-step

1. **Push to GitHub** — ensure your fork of `erikhinla/flow-as` is up to date.

2. **Import to Vercel**
   1. Go to <https://vercel.com/new>
   2. Click **Import** next to your forked repository (e.g., `yourusername/flow-as`).
   3. **Framework preset:** select *Other*.
   4. **Root directory:** leave blank (repo root).
   5. **Build command:** leave blank.
   6. **Output directory:** leave blank.

3. **Set environment variables**  
   In *Project → Settings → Environment Variables*, add the variables you need.
   See the table below for guidance.

4. **Deploy** — click *Deploy*. Vercel will install `requirements.txt` and serve `api/index.py`.

5. **Verify** — visit `https://<your-project>.vercel.app/healthz`. You should see:
   ```json
   { "status": "ok", "openai_api_key_set": true, ... }
   ```

### Required environment variables

Copy from [`.env.example`](.env.example) and set in the Vercel dashboard. **Never commit real secrets.**

| Variable | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | ✅ (or OpenRouter) | Use a real OpenAI key in production. |
| `OPENROUTER_API_KEY` | ✅ (or OpenAI) | Recommended for multi-model routing via Hermes. |
| `OPENAI_BASE_URL` | ⚠️ optional | **Do not** point this at a local Ollama instance (`http://ollama:…`). Use a publicly reachable URL or leave blank to use OpenAI's default. |
| `BIZBRAIN_API_TOKEN` | ✅ | Auth token for the FLOW control plane. |
| `MERCURY2_GATEWAY_TOKEN` | optional | Only needed if Mercury 2 agent is used. |
| `WEBHOOK_API_KEY` | optional | Protects the intake-webhook submissions endpoint. |
| `GITHUB_TOKEN` | optional | For GitHub integrations. |
| `DISCORD_TOKEN` | optional | Discord bot integration. |
| `TELEGRAM_BOT_TOKEN` | optional | Telegram bot integration. |
| `FIRECRAWL_API_KEY` | optional | Web-scraping integration. |

### Production notes

- **No local Ollama on Vercel.** Vercel functions are ephemeral and cannot reach Docker services. If your agents use `OPENAI_BASE_URL=http://ollama:11434/v1`, replace it with a publicly reachable Ollama server URL or use OpenAI/OpenRouter directly.
- **External database required.** The Vercel filesystem is ephemeral — any files written at runtime are lost between invocations. Use a managed Postgres provider (e.g., [Neon](https://neon.tech), [Supabase](https://supabase.com), [Railway](https://railway.app)) and set `DATABASE_URL` accordingly.
- **Redis.** For queue-based features use [Upstash Redis](https://upstash.com) and set `REDIS_URL`.
- **Long-running processes.** Vercel has a maximum function execution time. Background workers, agent loops, and Docker Compose services are **not** supported. Run those on a VPS or container platform (Fly.io, Render, Railway) and call them over HTTP from Vercel.
- **FLOW_DB_PASSWORD.** This is a Postgres password; it implies a running Postgres service. On Vercel, use a full `DATABASE_URL` connection string to a managed database instead.
