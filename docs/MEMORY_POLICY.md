# Memory Policy

Authority: _OS/02-Canon/CANONICAL_SOURCE_OF_TRUTH.md (Sections 6, 7)

## Purpose

Memory is the persistence layer. Its job is to preserve:

- decisions
- outputs
- lessons
- reflections
- changes
- reusable structures
- what the system should know next time

## Memory Destinations

All persisted outputs must go to a defined location:

| Output Type | Destination |
|---|---|
| Canon docs | _OS/02-Canon/ |
| Support docs | Brand repo docs/ |
| Execution logs | FLOW_AGENT_OS/runtime/logs/ |
| Task records | FLOW_AGENT_OS/runtime/tasks/ |
| Review artifacts | FLOW_AGENT_OS/reviews/ |
| Rollback plans | FLOW_AGENT_OS/rollback/ |
| Archived material | _OS/07-Archive/ |

## Reflection Records

After each completed task, the system records:

- what changed
- what worked
- what failed
- what was learned
- what is now unblocked
- what remains unresolved

## System Improvement

The system uses reflection to improve prompts, process, templates, memory, governance rules, routing logic, and implementation standards.

The next cycle begins with better context than the last one. That is how momentum compounds.
