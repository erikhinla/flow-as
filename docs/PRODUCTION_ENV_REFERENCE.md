# Production Env Reference

## Required

```env
A0_AUTH_LOGIN=admin
A0_AUTH_PASSWORD=change-me

BIZBRAIN_ENV=prod
BIZBRAIN_API_TOKEN=change-me
FLOW_DB_PASSWORD=change-me

OPENAI_API_KEY=sk-...

POSTIZ_DOMAIN=YOUR_HOST_OR_IP:5000
POSTIZ_JWT_SECRET=change-me
POSTIZ_DB_PASSWORD=change-me
```

## Optional

```env
GOOGLE_API_KEY=
GROQ_API_KEY=

MERCURY2_GATEWAY_TOKEN=change-me
MERCURY2_IMAGE=ghcr.io/erikhinla/mercury-2:latest

GITHUB_TOKEN=
DISCORD_TOKEN=
TELEGRAM_BOT_TOKEN=
FIRECRAWL_API_KEY=

SOCIAL_HUB_API_ORIGIN=http://YOUR_HOST_OR_IP:18000
POSTIZ_DISABLE_REGISTRATION=false

HERMES_DEFAULT_MODEL=gpt-4.1-mini
```

## Current Model Policy

- Hermes default: `gpt-4.1-mini`
- Anthropic and Claude are not part of the active deployment path
- OpenAI is the primary default
- Google and Groq are optional secondary providers

## Minimal Launch Configuration

If the immediate goal is to get FLOW live with the fewest moving parts, use only:

```env
A0_AUTH_LOGIN=admin
A0_AUTH_PASSWORD=change-me
BIZBRAIN_ENV=prod
BIZBRAIN_API_TOKEN=change-me
FLOW_DB_PASSWORD=change-me
OPENAI_API_KEY=sk-...
POSTIZ_DOMAIN=YOUR_HOST_OR_IP:5000
POSTIZ_JWT_SECRET=change-me
POSTIZ_DB_PASSWORD=change-me
HERMES_DEFAULT_MODEL=gpt-4.1-mini
```

## Notes

- Do not add `ANTHROPIC_API_KEY` or Claude session variables back into the active host `.env`.
- If secrets were pasted into chat or shared elsewhere, rotate them before production use.
- Keep rich input payloads out of the system when possible; prefer Markdown or stripped plain text.
