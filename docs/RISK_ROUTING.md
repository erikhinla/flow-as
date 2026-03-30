# Risk Routing

Authority: _OS/02-Canon/CANONICAL_SOURCE_OF_TRUTH.md + FLOW_AGENT_OS/docs/AGENT_ROLES.md

## Principle

Tasks are routed based on risk classification. Each agent operates at a specific risk tier.

## Risk Tiers

### Alpha (Low Risk) → OpenClaw
- Create folders and markdown files
- Move non-sensitive documents
- Classify artifacts into buckets
- Draft rewrite queues and migration ledgers

Worst case: wasted time, recoverable errors.

### Beta (Medium Risk) → OpenClaw
- Rewrite docs from canon
- Generate support and reference documentation
- Produce migration assets

Worst case: reputation-level errors (fixable).

### Operational → Hermes
- Execute bounded tasks from WIN governance
- Produce deliverables (docs, pages, playbooks)
- Generate content from canonical source material
- Report task completion with observable outputs

Worst case: incomplete deliverable (correctable).

### Gamma (High Risk) → Agent Zero
- Production deployment
- Domain and DNS changes
- Secrets management
- Infrastructure configuration
- Queue validation and schema enforcement
- Rollback preparation and execution

Worst case: downtime, security exposure, data loss.

## Escalation Flow

OpenClaw → Hermes (when deliverable generation exceeds file operations)
OpenClaw → Agent Zero (when task touches infra)
Hermes → Agent Zero (when task requires production deployment or secrets)
Agent Zero → HALT (if it cannot complete safely, it stops and reports)

## Required Outputs by Tier

| Tier | Required |
|---|---|
| Alpha/Beta | summary of changes |
| Operational | task_id, surface, files modified, canon validation, next WIN |
| Gamma | task.diff, task.review.md, task.rollback.md, validation result |
