# Intake Routing Logic
Authority: BIZBUILDERS/systems/intake/
Canon reference: ROUTING_RULES.md — Intake Routing, CANONICAL_SOURCE_OF_TRUTH.md Section 10

## Purpose

When a completed Context Architecture Assessment is submitted, this document
governs what happens next. Routing is based on observable gap indicators, not
subjective judgment.

---

## Scoring Model

Each section maps to one layer of the four-layer architecture.
A layer is flagged as a gap if one or more responses indicate instability.

| Section | Layer | Gap Indicators |
|---------|-------|----------------|
| Section 1 | Context (TransformBy10X) | source_of_truth = in_my_head or not_built; terminology_consistency = inconsistent; decision_framework = none |
| Section 2 | System Architecture (BizBuilders) | workflow_documentation = not_written or inconsistent; execution_paths = unclear; tooling = default or inconsistent; automation = below_30 or none |
| Section 3 | Activation (BizBot) | lead_capture = none; follow_up = reactive; content_system = none |
| Section 4 | Interface (Scale) | client_facing_accuracy = significant_gaps; intake_experience = ad_hoc |

---

## Routing Rules

### Rule 1 — 3 or more layers show gaps
**Route to:** BizBuilders full engagement conversation
**Response:** Observations across all flagged layers. No recommendation. Invite to a scoping call.

### Rule 2 — 2 layers show gaps
**Route to:** BizBuilders infrastructure conversation
**Response:** Observations on the two flagged layers. Note which layer must be resolved first per the canonical sequence.

### Rule 3 — 1 layer shows gaps
**Route to:** Targeted resource or single-layer recommendation
**Response:** Specific observation on the one flagged layer. Provide the relevant playbook or next step resource.

### Rule 4 — 0 layers show gaps
**Route to:** Acknowledge and monitor
**Response:** Confirm system stability. Offer periodic check-in or monitoring engagement.

---

## Sequence Enforcement

Routing must respect the canonical offer path sequence:

```
Context → System Architecture → Activation → Interface
```

If Section 1 (Context) shows gaps, it must be addressed before any work
on Sections 2, 3, or 4 is recommended. This rule is non-negotiable.

If a submission shows gaps only in Section 3 or 4 but not in Sections 1 or 2,
validate that Sections 1 and 2 are genuinely stable before routing to activation.

---

## Submission Handling

**Destination:** intake@bizbuilders.ai or INTAKE-SUBMISSION label in agent queue

**On receipt:**
1. Parse submission against schema (context-architecture-assessment.schema.json)
2. Flag gap count per layer
3. Apply routing rule
4. Draft response — observations only, no score, no recommendation, no pitch
5. Send within one business day

**Response format:**
- What we observed (layer by layer, only flagged layers)
- What that means operationally (plain language)
- What the next step is (one clear action, not a list of options)

---

## Anti-Drift Checks

Before sending any response:

- [ ] Response contains observations, not a sales pitch
- [ ] No score assigned
- [ ] No recommendation to skip layers in the canonical sequence
- [ ] No activation (BizBot) suggested before context and execution readiness are confirmed
- [ ] Language matches brand voice rules (clear, direct, operator-first)
