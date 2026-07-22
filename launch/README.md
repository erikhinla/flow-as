# TransformBy10X — launch hub

Static ecosystem site: TransformBy10X hub, Digital Fog Diagnostic, Digital Fog-Lift Kit, BizBuilders AI, and BizBot Mrktng.

## Production (canonical)

| What | Where |
|------|--------|
| Vercel team | **transformby10x** |
| Vercel project | **tbtx-cinema** |
| Preview URL | https://tbtx-cinema.vercel.app |
| Target domain | transformby10x.ai |

## Deploy

**From Git (preferred):**

1. Push branch to `https://github.com/erikhinla/flow-as` (connected to **tbtx-cinema**).
2. In Vercel → **tbtx-cinema** → Settings → General → set **Root Directory** = `launch` (one-time).
3. Production auto-deploys on push to the connected branch.

**From CLI:**

```bash
./scripts/deploy-tbtx.sh
```

**Live:** https://transformby10x.ai · https://tbtx-cinema.vercel.app

## Deprecated

- **bizbuilders-ai** on team *erik-bizbuilders' projects* — duplicate; redirect via `ops/deploy-legacy-bizbuilders-redirect.sh`
- **tbtx-web**, **tbtx-deploy** — legacy; do not deploy

## Routes

| Route | Canonical owner | Purpose |
|---|---|---|
| `/` | TransformBy10X | Ecosystem hub, Digital Fog, routing, campaign proof |
| `/diagnostic` | TransformBy10X | Digital Fog Diagnostic |
| `/foglift-kit` | TransformBy10X | Digital Fog-Lift Kit |
| `/bizbuilders-ai/` | BizBuilders AI | Operating architecture and governed execution |
| `/bizbuilders-ai/diagnostic` | BizBuilders AI | AI Infrastructure Assessment |
| `/bizbot-mrktng/` | BizBot Mrktng | Growth Products, Reddit package, RevAnew, and ArVA |

Legacy `/blueprint`, `/intellectual-ore`, `/infrastructure`, `/campaign`, `/field-note`, and `/bizbot` routes preserve entry traffic and forward into the canonical page sections. See `vercel.json`.
