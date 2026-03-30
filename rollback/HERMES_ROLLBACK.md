# Hermes Rollback

## Purpose
Define how to back Hermes out cleanly if setup introduces drift or unstable behavior.

## Rollback triggers
- Hermes conflicts with canon
- Hermes is positioned above FLOW Agent OS
- Hermes introduces new naming
- Hermes touches forbidden surfaces
- Hermes creates duplicate authority

## Rollback steps
1. Disable Hermes from active execution
2. Preserve logs and review artifacts
3. Move superseded Hermes files to:
   FLOW_AGENT_OS/archive/hermes-superseded/
4. Restore previous stable docs and prompts
5. Record rollback reason
6. Create follow-up review before reactivation

## Preserve before rollback
- generated outputs
- validation notes
- review notes
- state logs
- escalation records
