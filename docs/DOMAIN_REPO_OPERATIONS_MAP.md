# Domain, Repo, and Operations Map

This document maps domains, repositories, deployment targets, and operational
ownership across the FLOW Agent Architected Schemas (FAAS) ecosystem. Values
marked `TBD` or `decision required` are not production claims.

## Primary System: FLOW / FAAS Control Plane

- **Brand System:** FLOW Agent Architected Schemas (FAAS)
- **Domain:** TBD (private control-plane endpoint or approved subdomain)
- **Repo:** `flow-as`
- **Deploy Target:** Decision required before production promotion; existing
  runbooks reference Hostinger/VPS and Hetzner may be used for staging proof
- **Owner:** Erik
- **Core Function:** Governed orchestration, task routing, approval, evidence,
  audit, and final state for specialized worker lanes
- **First Worker Decision:** Hermes is a standalone FAAS-governed
  canon-and-learning execution worker; adapter implementation pending

## Property: TransformBy10X

- **Brand System:** TransformBy10X
- **Domain:** `transformby10x.ai`
- **Repo:** `tbtx-next-ecosystem`
- **Deploy Target:** TBD
- **Owner:** Erik
- **Core Function:** B2C Digital Fog entry layer, Fog Diagnostic, Fog Lift Kit delivery
- **Current Status:** Diagnostic question/answer logic reported complete by owner;
  design and deployment require proof linkage

## Property: BizBuilders AI

- **Brand System:** BizBuilders AI
- **Domain:** `bizbuilders.ai`
- **Repo:** TBD (independent repo or integrated in `tbtx-next-ecosystem`)
- **Deploy Target:** TBD
- **Owner:** Erik
- **Core Function:** B2B infrastructure/friction diagnostic and implementation path
- **Current Status:** Diagnostic logic reported complete by owner; design and
  deployment require proof linkage

## Property: BizBot Mktng

- **Brand System:** BizBot Mktng
- **Domain:** TBD
- **Repo:** TBD
- **Deploy Target:** TBD; gated downstream activation, not a first-wave launch
- **Owner:** Erik
- **Core Function:** Activation and growth execution surface after infrastructure preparation and FAAS installation

## Operational Ownership Matrix

| Function | Owner | System / Provider | Status |
| --- | --- | --- | --- |
| Canon and commercial activation decisions | Erik | FAAS operating layer | Active authority |
| Code review and merge approval | Erik | GitHub | Active authority |
| FAAS task routing, approval evidence, audit, terminal state | FAAS | `flow-as` | Control-plane code exists; worker contract reconciliation in progress |
| Hermes bounded artifact execution and reflection | Hermes under FAAS | Standalone worker + adapter | Planned, not deployed by current compose |
| FAAS production host | Erik | Hostinger or Hetzner role decision | Decision required |
| DNS administration | Erik | TBD | Decision required |
| Payment and fulfillment | Erik | TBD | Decision required |
| CRM and lead capture | Erik | TBD | Decision required |
| Analytics and attribution | Erik | TBD | Decision required |
