# Task Envelopes

Authority: _OS/02-Canon/CANONICAL_SOURCE_OF_TRUTH.md (Section 8)

## What a Task Envelope Is

A task envelope wraps a WIN into an executable unit for the execution engine.

## Required Fields

Every task envelope must contain:

| Field | Description |
|---|---|
| task_id | Unique identifier |
| statement | What is being done (the WIN) |
| surface | Where it lives (which repo, which directory) |
| outcome_type | What kind of result it produces |
| why_now | What stalls or breaks if not completed |
| risk_tier | Alpha, Beta, Operational, or Gamma |
| assigned_agent | OpenClaw, Hermes, or Agent Zero |

## Routing

The task envelope determines which agent receives the task based on risk_tier.

## Completion

A task envelope is only complete when:

- the intended outcome is observable
- the output is persisted to the correct repo location
- the output does not contradict _OS/02-Canon
- the next recommended WIN is declared

## Queue Flow

1. pending/ → task submitted
2. active/ → agent working
3. completed/ → outcome observed
4. escalated/ → risk exceeded agent tier
5. archive/ → historical record
