# Validation and Rollback

Authority: _OS/02-Canon/CANONICAL_SOURCE_OF_TRUTH.md (Section 16)

## Validation

Every output must be validated against:

1. Canonical terminology (NAMING_GLOSSARY.md)
2. Brand role clarity (BRAND_ROLES.md)
3. Offer path sequence (OFFER_PATH.md)
4. Anti-drift rules (ANTI_DRIFT_RULES.md)
5. Production criteria (Section 16)

### Production criteria for systems

- inputs defined
- outputs defined
- owner defined
- handoff defined
- memory destination defined
- rollback or validation logic defined where risk exists

## Rollback

Agent Zero requires a rollback plan before any Gamma-tier mutation.

### Rollback requirements

- Pre-change state documented
- Rollback steps defined
- Rollback tested or verifiable
- No direct production mutation without a review artifact

### Rollback artifacts

- task.diff (what changed)
- task.review.md (why it changed)
- task.rollback.md (how to undo it)
