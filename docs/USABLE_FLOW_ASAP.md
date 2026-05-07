# Usable FLOW ASAP

## Current Usable Slice

The fastest usable slice is the diagnostic intake flow in `intake-webhook`.

It provides:
- routing page: `GET /`
- TransformBy10X B2C diagnostic: `GET /diagnostic?type=tbtx`
- BizBuilders AI B2B diagnostic: `GET /diagnostic?type=bizbuilders`
- diagnostic submission API: `POST /diagnostic/submit`
- stored JSON submissions under the `intake_data` Docker volume
- submission listing: `GET /intake/submissions?api_key=...`

## Local Docker URL

After starting Compose, open:

```bash
http://localhost:18080/
```

TransformBy10X:

```bash
http://localhost:18080/diagnostic?type=tbtx
```

BizBuilders AI:

```bash
http://localhost:18080/diagnostic?type=bizbuilders
```

Health check:

```bash
curl -s http://localhost:18080/health
```

View recent submissions:

```bash
curl -s "http://localhost:18080/intake/submissions?api_key=$WEBHOOK_API_KEY"
```

## What It Does

1. Captures name, email, company, role, and industry.
2. Asks scored diagnostic questions tailored to B2C or B2B.
3. Calculates a score.
4. Assigns a category.
5. Produces an industry-aware diagnosis.
6. Identifies top infrastructure gaps.
7. Produces a phased plan and highest-leverage next move.
8. Routes the next CTA to BizBuilders AI or BizBot Mktng depending on diagnostic type.
9. Persists the complete lead/session/answer/report record as JSON.

## Diagnostic Models

TransformBy10X is B2C and uses the Digital Fog Diagnostic. It focuses on personal execution clarity, attention, AI readiness, handoff, and the quad keystone.

BizBuilders AI is B2B and uses the Infrastructure Readiness Diagnostic. It focuses on offer clarity, buyer specificity, CRM, qualification, delivery, analytics, governance, automation, and scale readiness.

Both models map answers to reusable dimensions:
- folders and source of truth
- markdowns and reusable knowledge
- scripts and repeatable steps
- protocols and decision rules
- lead capture
- handoff
- offer clarity
- analytics
- AI readiness

## Still Bounded

This is usable for controlled intake and testing. It does not yet:
- sync to CRM
- create Supabase records
- take payments
- send fulfillment emails
- map production domains
- publish legal pages
