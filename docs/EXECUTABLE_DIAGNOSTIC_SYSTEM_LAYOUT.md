# Executable Diagnostic System Layout

This document defines a reusable diagnostic architecture spanning TransformBy10X, BizBuilders AI, and BizBot Mktng.

## Source Assets

- `Diagnostic.tsx`: questions, scoring logic, and result categories.
- `AssessmentFlow.tsx`: lead capture, multi-step UX, assessment progression, and results handoff.
- Chad AI Bridge: personalized roadmap model from intake to system map to flows to W.I.N.
- FLOW interactive page: orchestration explainer for agent, workflow, memory, and handoff visualization.

## Core Component

### DiagnosticEngine

Inputs:
- Diagnostic type
- Question set
- Scoring rules
- Lead fields
- Redirect target

Outputs:
- Session ID
- Lead record
- Answers
- Score
- Category
- Dimension scores
- Industry-aware diagnosis
- Top gaps
- Recommended infrastructure
- Phased plan
- Highest-leverage next move

## User Flow

1. Landing page
2. Lead capture
3. Diagnostic questions
4. Score + category
5. Roadmap preview
6. CTA routing

## Site Routing

- TransformBy10X `/diagnostic`
  - Digital Fog Score
  - CTA: Get Your Custom Roadmap
- BizBuilders AI `/roadmap`
  - AI Custom Roadmap
  - CTA: Activate Growth System
- BizBot Mktng
  - Execution handoff target

## Implemented Local MVP Routes

- `/` diagnostic chooser
- `/diagnostic?type=tbtx` TransformBy10X B2C Digital Fog Diagnostic
- `/diagnostic?type=bizbuilders` BizBuilders AI B2B Infrastructure Readiness Diagnostic
- `/diagnostic/submit` scored submission endpoint

## Data Flow

1. User submits lead.
2. Create diagnostic session.
3. Store answers.
4. Calculate score.
5. Generate category.
6. Create dimension scores.
7. Generate industry-aware diagnosis and phased plan.
8. Route to next offer.

## Backend Structure

### Supabase Tables

#### `leads`
- `id`
- `name`
- `email`
- `source`
- `created_at`

#### `diagnostic_sessions`
- `id`
- `lead_id`
- `diagnostic_type`
- `score`
- `category`
- `roadmap_seed`
- `utm_source`
- `utm_campaign`
- `created_at`

#### `diagnostic_answers`
- `id`
- `session_id`
- `question_id`
- `answer_value`
- `answer_label`

#### `events`
- `id`
- `lead_id`
- `event_type`
- `page`
- `metadata`
- `created_at`

## Roadmap Output

AI Custom Roadmap sections:
- Industry context
- Current workflow breakdown
- AI leverage opportunities
- System gaps
- Recommended infrastructure
- Phased implementation plan
- Highest-leverage next move

## Cross-Site CTA System

- TransformBy10X: Find the Gaps
- BizBuilders AI: Get Your Custom Roadmap
- BizBot Mktng: Activate Growth System

## Execution Rule

One diagnostic engine, multiple configurations.

Guardrails:
- No scattered quiz logic
- No dead-end CTAs
- No fake completion
- No claims without artifacts

## Layered System Map

```text
TRANSFORMBY10X
Philosophy + Entry Layer
Digital Fog Campaign
  -> DiagnosticEngine
  -> Score + Category
  -> CTA: Get Your Custom Roadmap

BIZBUILDERS AI
Infrastructure + Roadmap Layer
AI Custom Roadmap
  -> Roadmap Preview
  -> System Gap Map
  -> CTA: Activate Growth System

BIZBOT MKTNG
Execution + Growth Layer
RevAnew
  -> Reddit Growth Suite
  -> Execution Pipeline
```
