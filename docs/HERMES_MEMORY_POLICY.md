# Hermes Memory Policy

## Purpose
Hermes must preserve useful execution context without becoming a second source of truth.

## Memory principle
Memory supports execution.
Memory does not replace canon.

## Write destinations
Hermes writes memory to:

- FLOW_AGENT_OS/memory/hermes/decisions/
- FLOW_AGENT_OS/memory/hermes/outputs/
- FLOW_AGENT_OS/memory/hermes/reflections/
- FLOW_AGENT_OS/memory/hermes/state/

## What Hermes should store
### Decisions
- task decisions
- scope clarifications
- escalation decisions
- validation outcomes

### Outputs
- file creation records
- generated artifacts
- rewrite results
- completed task summaries

### Reflections
- what worked
- what failed
- what needs tightening
- what should change next time

### State
- current task status
- blocked status
- awaiting review
- awaiting escalation

## What Hermes should not store as memory authority
- business doctrine
- final naming rules
- brand architecture
- canonical sequence
- public positioning

Those belong in canon.

## Memory rule
Every memory write should reference:
- task
- date
- surface
- status
- next step
