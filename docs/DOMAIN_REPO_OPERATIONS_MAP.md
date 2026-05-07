# Domain, Repo, and Operations Map

This document serves as the canonical source of truth for mapping domains, code repositories, deployment targets, and operational ownership across the FLOW Agent OS (FAAS) ecosystem.

## Primary System: FLOW/FAAS Control Plane
- **Brand System:** FLOW Agent Architected Schemas (FAAS)
- **Domain:** TBD (e.g., `flow-as.example.com` or private IP)
- **Repo:** `flow-as`
- **Deploy Target:** Hostinger/VPS (Docker Compose Runtime)
- **Owner:** Erik
- **Core Function:** Governed orchestration, task routing, intake queues, execution runtime.

## Property: TransformBy10X
- **Brand System:** TransformBy10X
- **Domain:** `transformby10x.ai`
- **Repo:** `tbtx-next-ecosystem`
- **Deploy Target:** Vercel (extrapolated) / TBD
- **Owner:** Erik
- **Core Function:** B2C Digital Fog entry layer, Fog Diagnostic, Fog Lift Kit delivery.

## Property: BizBuilders AI
- **Brand System:** BizBuilders AI
- **Domain:** `bizbuilders.ai`
- **Repo:** TBD (assumed either independent repo or integrated in `tbtx-next-ecosystem`)
- **Deploy Target:** TBD
- **Owner:** Erik
- **Core Function:** B2B Infrastructure Readiness Diagnostic, Custom Roadmap generation.

## Property: BizBot Mktng
- **Brand System:** BizBot Mktng
- **Domain:** TBD (e.g., `bizbotmktng.com`)
- **Repo:** TBD
- **Deploy Target:** TBD
- **Owner:** Erik
- **Core Function:** Activation and growth execution surface, Reddit Marketing Guide, RevAnew.

## Operational Ownership Matrix
| Function | Owner | System/Provider |
|---|---|---|
| **Code Review & Deployment** | Erik | GitHub -> Hostinger VPS / Vercel |
| **DNS Administration** | Erik | TBD (e.g., Cloudflare/Namecheap) |
| **Payment & Fulfillment** | Erik | TBD (e.g., Stripe) |
| **CRM & Lead Capture** | Erik | TBD (e.g., HubSpot / HighLevel) |
| **Analytics & Attribution** | Erik | TBD (e.g., PostHog / GA4) |
