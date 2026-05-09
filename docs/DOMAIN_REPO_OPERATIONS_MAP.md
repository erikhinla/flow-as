# Domain, Repo, and Operations Map

This document serves as the canonical source of truth for mapping domains, code repositories, deployment targets, and operational ownership across the FLOW Agent AS / F.A.A.S. ecosystem.

Current posture: two public sites first. BizBot Marketing is a premium BizBuilders unlock, not a separate public URL unless that decision is changed later.

## Primary System: FLOW/FAAS Control Plane
- **Brand System:** FLOW Agent Architected Schemas (FAAS)
- **Domain:** TBD (e.g., `flow-as.example.com` or private IP)
- **Repo:** `FLOW-AGENT-AS`
- **Deploy Target:** Hostinger/VPS (Docker Compose Runtime)
- **Owner:** Erik
- **Core Function:** Governed orchestration, task routing, intake queues, execution runtime.

## Property: TransformBy10X
- **Brand System:** TransformBy10X
- **Domain:** `transformby10x.ai`
- **Repo:** `tbtx-next-ecosystem`
- **Deploy Target:** Vercel (extrapolated) / TBD
- **Owner:** Erik
- **Core Function:** B2C doctrine/philosophy site, AI Preparedness and Digital Fog diagnostic, `$7 / $27 / $97` offer ladder, founder story, proof of work, and bridge to BizBuilders AI.

## Property: BizBuilders AI
- **Brand System:** BizBuilders AI
- **Domain:** `bizbuilders.ai`
- **Repo:** `tbtx-next-ecosystem` unless split later
- **Deploy Target:** TBD
- **Owner:** Erik
- **Core Function:** B2B lead generation, AVA-guided infrastructure assessment, blueprint generation, schedule-call handoff, and premium BizBot Marketing unlock.

## Premium Unlock: BizBot Marketing
- **Brand System:** BizBot Mktng
- **Domain:** Internal route only (no separate public URL)
- **Repo:** `tbtx-next-ecosystem`
- **Deploy Target:** Same as BizBuilders AI
- **Owner:** Erik
- **Core Function:** Premium growth layer unlocked inside BizBuilders AI after infrastructure assessment context. Accessed via qualified lead flow. Includes RevAnew, Reddit Account Growth Engine, Account Intelligence Report, Marketing Blueprint, and Social Automation Starter Kit.

## Operational Ownership Matrix
| Function | Owner | System/Provider |
|---|---|---|
| **Code Review & Deployment** | Erik | GitHub -> Hostinger VPS / Vercel |
| **DNS Administration** | Erik | TBD (e.g., Cloudflare/Namecheap) |
| **Payment & Fulfillment** | Erik | TBD (e.g., Stripe) |
| **CRM & Lead Capture** | Erik | TBD (e.g., HubSpot / HighLevel) |
| **Analytics & Attribution** | Erik | TBD (e.g., PostHog / GA4) |
