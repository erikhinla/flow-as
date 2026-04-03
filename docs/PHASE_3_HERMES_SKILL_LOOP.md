# Phase 3: Hermes Skill Extraction Loop

## Overview

Hermes implements the **recursive learning loop** for FLOW Agent OS.

**Flow:**
```
1. Job completes
   ↓
2. Agent writes reflection (what_worked, what_failed, pattern_observed)
   ↓
3. Background job reads reflections (every 5 min)
   ↓
4. Hermes checks: is pattern extractable?
   ↓
5. YES → Create/update skill_record, index by task_type + context
   ↓
6. NO → Skip (one-off work, no pattern)
   ↓
7. Next similar task arrives
   ↓
8. Retrieve skills for that task_type + context
   ↓
9. Enrich execution context with top-3 skills
   ↓
10. Execute with prior knowledge
    ↓
11. Track outcome: did skill help?
    ↓
12. Update confidence: +0.1 if success, -0.15 if failure
```

---

## What Was Built

### 1. SkillExtractionService (`skill_extraction_service.py`)

Core service handling all skill operations:

**Methods:**

- `should_extract_skill(reflection)` → Checks if reflection has extractable pattern
  - Validates: has_pattern, is_repeatable, success_clear, tool_sequence_defined
  - Returns: (bool, checks_dict)

- `extract_skill(db, reflection)` → Creates or updates skill_record
  - If similar skill exists: reinforce (don't duplicate)
  - If new: create with confidence=0.5
  - Returns: skill_id

- `retrieve_skills_for_task(db, task_type, context_type, limit=3)` → Get applicable skills
  - Query by task_type + context, order by confidence DESC
  - Marks status as 'experimental' if confidence < 0.4
  - Used to enrich task context before execution

- `update_skill_confidence(db, skill_id, task_succeeded)` → Track success/failure
  - Success: +0.1 confidence
  - Failure: -0.15 confidence
  - Retire if: confidence < 0.2 AND times_used > 5

- `process_pending_reflections(db)` → Batch process all pending reflections
  - Runs every 5 minutes
  - Extracts up to 100 reflections per pass
  - Returns: {extracted, skipped, errors}

### 2. Hermes Skills API (`hermes_skills.py`)

REST endpoints for the skill loop:

**POST `/v1/hermes/reflections`** — Write reflection
```json
{
  "task_id": "task-123",
  "job_id": "job-456",
  "owner": "openclaw",
  "what_worked": "Regex matched 95% correctly",
  "what_failed": "Edge cases with special chars",
  "pattern_observed": "Submissions follow header+body pattern",
  "context_type": "intake_form",
  "tool_sequence": ["regex_match", "fallback_rule", "json_output"],
  "success_signal": "All files classified with confidence >= 0.9"
}
```

**POST `/v1/hermes/extract-skills`** — Trigger extraction pass
- Processes all pending reflections
- Returns: {extracted: N, skipped: N, errors: N}

**GET `/v1/hermes/skills?task_type=classification&context_type=intake_form&limit=3`** — Retrieve skills
- Returns top-3 skills ordered by confidence
- Marks status as 'trusted' (confidence >= 0.4) or 'experimental'

**POST `/v1/hermes/skills/{skill_id}/feedback`** — Update confidence
```json
{
  "task_succeeded": true,
  "notes": "Regex worked perfectly"
}
```

**GET `/v1/hermes/skills/{skill_id}`** — Get specific skill

### 3. Background Extraction Job (`skill_extraction_job.py`)

Periodic job that processes reflections:

**How it runs:**
- On app startup: creates SkillExtractionJob
- Every 5 minutes: calls `process_pending_reflections()`
- On app shutdown: stops cleanly

**Integration:**
```python
# In main.py (already added)
@app.on_event("startup")
async def startup_skill_extraction():
    global skill_extraction_job
    skill_extraction_job = SkillExtractionJob(interval_seconds=300)
    asyncio.create_task(skill_extraction_job.start())

@app.on_event("shutdown")
async def shutdown_skill_extraction():
    global skill_extraction_job
    if skill_extraction_job:
        await skill_extraction_job.stop()
```

---

## Confidence Model

Skills track effectiveness over time.

**Confidence score:** 0.0 to 1.0

**Updates:**
- Start: 0.5
- Success: +0.1 (capped at 1.0)
- Failure: -0.15 (floors at 0.0)

**Lifecycle:**
```
0.5 (new) → 0.6 (first success) → 0.7 (repeated success)
          ↓
         0.55 (one failure) → 0.40 (two failures) → LOW_CONFIDENCE
          ↓
         0.25 (three failures) → RETIRED (if times_used > 5)
```

**Status transitions:**
- `active` → `low_confidence` (if confidence < 0.4)
- `low_confidence` → `active` (if confidence > 0.4 again)
- `active/low_confidence` → `retired` (if very low confidence + repeated failures)

---

## Example Flow

### Task 1: Classify intake submissions

1. **Agent executes** classification task
2. **Success:** 98% of submissions classified correctly
3. **Reflection written:**
   ```json
   {
     "task_id": "task-intake-1",
     "job_id": "job-123",
     "owner": "openclaw",
     "what_worked": "Regex pattern matched 98/100 submissions on first pass",
     "pattern_observed": "Intake submissions follow predictable header+body pattern",
     "context_type": "intake_form",
     "tool_sequence": ["regex_match", "fallback_rule", "json_output"],
     "success_signal": "All 100 files classified with confidence >= 0.9"
   }
   ```

4. **Extraction job runs** (5 min later)
   - Checks: has_pattern=YES, success_clear=YES, tool_sequence=YES
   - Decision: EXTRACT
   - Creates: SkillRecord with confidence=0.5

5. **Skill indexed:**
   - Name: `openclaw__intake_form__abc12345`
   - Task type: classification
   - Context: intake_form
   - Pattern: "Submissions follow predictable header+body pattern"
   - Tools: ["regex_match", "fallback_rule", "json_output"]
   - Confidence: 0.5

### Task 2: Classify different batch of intake submissions

1. **Before execution**, agent requests skills:
   ```
   GET /v1/hermes/skills?task_type=classification&context_type=intake_form
   ```

2. **Response:**
   ```json
   [
     {
       "skill_id": "skill-456",
       "name": "openclaw__intake_form__abc12345",
       "pattern": "Submissions follow predictable header+body pattern",
       "tool_sequence": ["regex_match", "fallback_rule", "json_output"],
       "confidence": 0.5,
       "status": "experimental"
     }
   ]
   ```

3. **Execution context enriched** with skill suggestion
4. **Agent uses the skill** → executes faster, more confidently
5. **Success:** 99% classified
6. **Feedback posted:**
   ```
   POST /v1/hermes/skills/skill-456/feedback
   {
     "task_succeeded": true,
     "notes": "Skill worked great, only 1 edge case"
   }
   ```

7. **Confidence updated:**
   - New confidence: 0.5 + 0.1 = 0.6
   - Status: still `active`
   - Success rate: 2/2 (100%)

### Task 3: Classify again

1. Retrieve skills → now confidence=0.6 (marked as 'trusted')
2. Execute with higher confidence
3. Slight failure (97% success)
4. Feedback: task_succeeded=false
5. Confidence updated: 0.6 - 0.15 = 0.45
6. Status: remains `active` (still > 0.4)

### Task 4-5: Multiple failures

1. Retrieve skills → confidence=0.45 (still 'trusted')
2. Execute → 85% success
3. Feedback: false → confidence = 0.30
4. Status: `low_confidence` (< 0.4)

On next retrieval, skill marked as `experimental`. Use with caution.

---

## Testing the Skill Loop

### 1. Write a reflection

```bash
curl -X POST http://localhost:8000/v1/hermes/reflections \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-123",
    "job_id": "job-456",
    "owner": "openclaw",
    "what_worked": "Regex pattern worked",
    "what_failed": "None",
    "pattern_observed": "Files follow consistent format",
    "context_type": "intake_form",
    "tool_sequence": ["regex_parse", "json_write"],
    "success_signal": "All 50 files processed"
  }'
```

Response:
```json
{
  "reflection_id": "refl-789",
  "task_id": "task-123",
  "skill_extraction_attempted": "N"
}
```

### 2. Trigger extraction manually

```bash
curl -X POST http://localhost:8000/v1/hermes/extract-skills
```

Response:
```json
{
  "extracted": 1,
  "skipped": 0,
  "errors": 0
}
```

### 3. Retrieve skills

```bash
curl http://localhost:8000/v1/hermes/skills?task_type=classification&context_type=intake_form
```

Response:
```json
[
  {
    "skill_id": "skill-123",
    "name": "openclaw__intake_form__xyz",
    "task_type": "classification",
    "confidence": 0.5,
    "times_used": 1,
    "times_succeeded": 1,
    "status": "experimental"
  }
]
```

### 4. Give feedback

```bash
curl -X POST http://localhost:8000/v1/hermes/skills/skill-123/feedback \
  -H "Content-Type: application/json" \
  -d '{"task_succeeded": true}'
```

Response:
```json
{
  "skill_id": "skill-123",
  "confidence": 0.6,
  "times_used": 2,
  "times_succeeded": 2,
  "success_rate": "100.00%"
}
```

---

## Key Features

✓ **Non-duplicate skills** — If similar skill exists, reinforce instead of creating duplicate  
✓ **Confidence-based ranking** — Retrieve top skills by confidence  
✓ **Experimental marking** — Low-confidence skills marked as experimental  
✓ **Auto-retirement** — Skills below confidence threshold marked as retired  
✓ **Batch processing** — Extract 100 reflections per pass (scalable)  
✓ **Background job** — Runs every 5 minutes without blocking requests  
✓ **Asyncio native** — All database ops are async/await  

---

## Next Phase

Phase 4: **OpenClaw envelope validation + routing**

OpenClaw will:
- Validate task envelopes against schema
- Route to correct owner (openclaw, hermes, agent_zero)
- Check business rules (high-risk must have review_required, etc.)
- Enqueue tasks into Redis
