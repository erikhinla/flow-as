# Hermes Agent Overview

## Status
Architecture decision recorded; FAAS worker adapter pending implementation.

## Canonical Position

FAAS means **FLOW Agent Architected Schemas**.

FAAS is the governed execution and proof layer coordinating specialized AI
workers. Hermes is a **FAAS-governed canon-and-learning execution worker**.
Hermes may run as a standalone service, but it remains subordinate to FAAS
routing, risk policy, approval gates, evidence requirements, and final state.

Hermes is not doctrine, not activation, not interface, not the Execution
Engine, and not a runtime governor.

## Authority Model

| Authority | Owner |
| --- | --- |
| Canon, priorities, production approvals, commercial activation decisions | Erik |
| Work orders, task envelopes, routing, risk tiers, approvals, evidence, audit trail, final state | FAAS |
| Canon-aware synthesis, bounded artifact production, reflections, skill learning | Hermes |

## Purpose

Hermes carries a FAAS-assigned, declared WIN into structured execution outputs
without bypassing the governed proof loop.

## Primary Job

Take bounded execution tasks and return observable, persisted artifacts plus a
status, reflection, and proof record that FAAS can accept, reject, or escalate.

## What Hermes Can Help Produce

- structured docs
- task records
- implementation specifications
- validation-ready outputs
- execution summaries
- update records
- rewrite drafts tied to canon
- classified artifacts
- migration support files
- structured reflections and reusable skills

## What Hermes Cannot Authorize

Hermes must escalate rather than independently perform:

- production deployment
- secret handling or rotation
- billing or payment changes
- DNS changes
- database mutations
- destructive file operations
- canon redefinition or brand repositioning
- rollback-sensitive runtime changes

## Adapter Boundary

A standalone Hermes service does not become part of FAAS merely because it is
installed. A FAAS Hermes Worker Adapter must mediate all governed work.

The adapter must:

1. receive only FAAS-routed Hermes task envelopes;
2. atomically claim a `task_id` before execution;
3. refuse duplicate running work and return completed results on replay;
4. enforce Hermes risk-tier permissions;
5. create an isolated workspace per task;
6. invoke Hermes for bounded artifact production;
7. write status, artifacts, reflection, and proof back through FAAS APIs only;
8. acknowledge queue work only after FAAS accepts the write-back.

## Definition Of Done

A Hermes task is done only when the intended output exists in the correct
location, its proof is reviewable, and FAAS records the task as complete.
