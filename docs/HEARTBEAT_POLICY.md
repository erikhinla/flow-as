# Heartbeat Policy

Authority: _OS/02-Canon/CANONICAL_SOURCE_OF_TRUTH.md (Section 7)

## Purpose

The heartbeat is the periodic check that keeps the execution engine aligned with canon.

## Heartbeat Checks

At each heartbeat interval:

1. Is the current WIN still valid?
2. Has the active task completed?
3. Are there escalated items waiting?
4. Has any output drifted from canon?
5. Is the memory layer current?

## Frequency

Heartbeat runs at the cadence appropriate to the active task.
Short tasks: per-step.
Long tasks: periodic intervals.

## What Heartbeat Produces

- Status update (running, completed, blocked, escalated)
- Canon compliance check (pass/fail)
- Next action recommendation
