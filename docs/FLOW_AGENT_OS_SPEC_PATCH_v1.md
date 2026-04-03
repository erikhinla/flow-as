# FLOW_AGENT_OS_SPEC_PATCH_v1

## Status
Locked patch layer for FLOW Agent OS implementation spec.

## Purpose
This patch closes the implementation gaps identified during architecture and repo review so FLOW Agent OS can move from sound theory to governed execution.

This patch is subordinate to the locked implementation spec.
It tightens the implementation path.
It does not replace canon.

---

## 1. Status migration is required before enum cutover

Current implementations using legacy states such as:
- pending
- in_progress
- completed
- failed
- escalated

must migrate explicitly to the locked status model:
- pending
- validated
- queued
- active
- review_required
- completed
- failed
- dead_letter
- blocked
- escalated
- archived

### Required rules
- `in_progress` must migrate to `active`
- no task may retain legacy statuses after migration completes
- migration must be recorded and reversible
- enum cutover must not happen without a migration plan

---

## 2. `task_type` and `risk_tier` are required

No task envelope is valid unless it includes:
- `task_type`
- `risk_tier`

### Required rules
- envelope validation must fail if either field is missing
- routing must not proceed without both fields present
- these are required routing fields, not optional metadata

---

## 3. Intake must enter the governed registry flow

Any intake surface that writes flat JSON directly to disk without creating a governed task record creates a parallel truth.

### Required rules
All intake paths must POST into the governed registry flow.

No intake path may bypass:
- task record creation
- owner assignment
- status tracking
- reflection eligibility
- skill-loop eligibility

### Prohibited
- raw file drop as final intake
- flat JSON task files with no registry entry
- shadow queues outside the registry

---

## 4. `source` and `owner` must be distinct

`source` and `owner` must not be conflated.

### Definitions
- `source` = where the task entered the system
- `owner` = which worker is responsible for execution

### Example
- source: `webhook`
- owner: `openclaw`

### Required rules
- both fields must exist independently on the job record
- routing logic must read `owner`
- observability and audit logic must preserve `source`

---

## 5. Handoff endpoint is the only legal cross-agent path

“No direct agent-to-agent communication” must be technically enforced.

### Required rules
All cross-agent transfer must occur through:
- handoff record
- handoff endpoint
- broker-mediated routing

### Prohibited
- direct worker-to-worker calls
- hidden side-channel routing
- ad hoc envelope mutation outside handoff recording

---

## 6. Reflection records must support confidence updates

Reflection records must carry the fields required for Hermes confidence updates.

### Add required fields
- `skills_used`
- `skill_helped`

### Definitions
- `skills_used` = list of skill IDs injected into execution context
- `skill_helped` = boolean or structured indicator showing whether the skill materially improved the outcome

### Required rules
- confidence must not be updated without explicit reflection evidence
- Hermes confidence updates must be tied to reflection records, not inferred folklore

---

## 7. Reflection validation is required before skill extraction

Not every reflection should become a skill candidate.

### Required rules
A reflection qualifies for skill extraction only if all are true:
- task type is repeatable
- success signal is observable
- pattern is clear enough to reuse
- tool sequence is identifiable
- output is not a one-off accident

### If validation fails
- reflection remains stored
- no skill record is created
- no confidence update occurs

---

## 8. Skill retrieval must use ranked retrieval, not scan-all patterns

Skill retrieval must not rely on scanning every skill record and filtering in application logic.

### Required rules
- Redis hot-state retrieval should use sorted sets or equivalent ranked retrieval
- Postgres remains the durable skill store
- retrieval should return top-ranked candidate skills for the incoming task

### Default retrieval behavior
- retrieve top 3 matching skills
- any skill with confidence below `0.4` must be marked `experimental`
- experimental skills may inform execution but must not dominate routing or override higher-confidence skills

---

## 9. Thread metadata is the preferred skill-context carrier

Where a task or session thread model already exists, retrieved skill summaries should be attached to thread metadata rather than inventing a second enrichment mechanism.

### Required rules
- skill summaries may be injected into thread context
- raw full skill records should not be blindly stuffed into prompts
- execution context should remain compact and relevant

---

## 10. Skill retirement rules must be explicit

### Required rules
A skill must be marked `low_confidence` or `retired` if it repeatedly fails.

### Default retirement logic
- start confidence at `0.5`
- success with reuse: `+0.1`
- repeated success: `+0.05`
- failure on reuse: `-0.15`
- repeated failure or confidence falling below `0.2` triggers retirement review

### Allowed statuses
- `active`
- `low_confidence`
- `retired`

---

## 11. Dead-letter ownership and retry policy must be explicit

### Required rules
When a job fails repeatedly:
- mark `failed`
- preserve payload
- preserve logs
- preserve owner history
- move to `dead_letter` after retry threshold
- require explicit retry authorization

### Prohibited
- silent retry loops
- hidden requeue behavior
- ownership loss after failure

---

## 12. Intake webhook must default deny on missing auth configuration

If an intake endpoint can accept submissions when an expected environment variable is missing, that is a pre-production blocker.

### Required rules
- intake authentication must default deny
- missing auth configuration must fail closed
- missing secret configuration must generate explicit error logging

---

## 13. Mirror failures must not be silent

Until full durable Postgres state is live, mirror failures must still surface.

### Required rules
- any `_mirror_safely` failure must emit minimum error logging
- mirror errors must be queryable in logs
- silent durability loss is not acceptable

---

## 14. Agent Zero execution must be technically blocked without review artifacts

The review gate must not be documentary only.

### Required rules
Agent Zero may not execute if any of the following are missing:
- `task.diff`
- `task.review.md`
- `task.rollback.md`

### Prohibited
- implied approval
- fallback execution without artifacts
- production mutation before review gate passes

---

## 15. Implementation priority update

The next implementation order is tightened as follows:

### First
- patch the spec with this document
- lock status migration plan
- add `task_type` and `risk_tier` to the task model
- close the intake parallel-truth gap

### Second
- implement Postgres-backed `job_records`
- implement Postgres-backed `reflection_records`
- implement Postgres-backed `skill_records`

### Third
- implement Hermes skill extraction
- implement top-3 ranked skill retrieval
- implement confidence updates and retirement rules

### Fourth
- enforce handoff endpoint only
- enforce dead-letter and retry ownership
- block Agent Zero without review artifacts

---

## Settled patch truth

FLOW Agent OS is close, but these controls are required to make the implementation durable, governable, and actually recursive instead of merely reflective.

This patch is now part of the locked implementation path.
