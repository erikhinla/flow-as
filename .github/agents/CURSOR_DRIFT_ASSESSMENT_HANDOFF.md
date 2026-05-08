# CURSOR: FLOW Agent AS Drift Assessment Task (v1.1.0)

**Status:** Ready for handoff  
**Priority:** P0 (Production validation + learning loop proof)  
**Authority:** Full execution delegation  
**Timeline:** Execute, monitor, report completion  

---

## CONTEXT: What This Task Does

**v1.0.0 (completed):**
- Generated Reddit content (3 comments + 1 post)
- Execution time: 6.75 seconds
- Artifact: 2,776 bytes
- Status: ✅ Production proven

**v1.1.0 (this task - drift assessment):**
- Execute same content generation (v1.0.0 logic)
- **ADD:** Reflection loop (score each comment 1-10 on 4 dimensions)
- **ADD:** Learning loop (generate improved prompting rules for next cycle)
- **ADD:** Comparative analysis (what changed, what improved, why)
- Test whether FLOW can learn and adapt, not just repeat

**Why this matters:**
- v1.0.0 proved FLOW executes
- v1.1.0 proves FLOW can improve itself
- This is the difference between automation and intelligence

---

## THE TASK SPECIFICATION

```yaml
version: "1.1.0"
mode: "build"
task_id: "pc_reddit_cycle_v1_1_0"
title: "Prompting Circumstance — Reddit Growth Cycle + Reflection"

created_by: "human"
owner_role: "alpha"
risk_tier: "reputation"

objective: >
  Execute a Prompting Circumstance Reddit content cycle,
  generate community-native outputs, and run a reflection
  loop that scores performance and improves the next cycle.

context:
  system: "Prompting Circumstance"
  channel: "reddit"

inputs:
  target_subreddits:
    - "r/Entrepreneur"
    - "r/marketing"
    - "r/startups"

  content_theme: >
    Infrastructure vs tools. Why most people fail with AI
    because they focus on tools instead of systems.

  tone_rules:
    - "sound like a power user"
    - "no marketing language"
    - "short, direct, observational"
    - "no forced engagement"

---

execution:

  step_1_generate:
    action: "generate_content"
    output:
      comments: 3
      post: 1

    constraints:
      comments:
        - "under 120 words"
        - "add insight, not summary"
      post:
        - "under 180 words"
        - "invite discussion without asking"

  step_2_queue:
    action: "submit_to_flow"
    requirements:
      - "schema validation"
      - "job_id returned"

  step_3_lifecycle:
    action: "monitor_execution"
    verify:
      - "pending → active → completed"
      - "execution under 15 seconds"

  step_4_artifact:
    action: "write_outputs"
    paths:
      - "/state/artifacts/pc_reddit_cycle/output.md"
      - "/state/artifacts/pc_reddit_cycle/metadata.json"

---

reflection:

  step_5_bizbrain:
    action: "analyze_outputs"

    evaluate:
      for_each_comment:
        - clarity_score: "1-10"
        - usefulness_score: "1-10"
        - authenticity_score: "1-10"
        - likely_upvote_potential: "1-10"

    select:
      best_comment: "highest combined score"
      weakest_comment: "lowest combined score"

    insights:
      - "what made the best comment strong"
      - "what made the weakest comment weak"
      - "pattern differences"

    output:
      path: "/state/artifacts/pc_reddit_cycle/reflection.md"

---

learning:

  step_6_prompt_update:
    action: "refine_prompting"

    generate:
      improved_rules:
        - "what to do more of"
        - "what to avoid"

      next_cycle_adjustments:
        - "tone shift"
        - "structure tweak"
        - "angle refinement"

    output:
      path: "/state/artifacts/pc_reddit_cycle/next_prompt.md"

---

audit:

  required_events:
    - "job_submitted"
    - "job_queued"
    - "job_started"
    - "job_completed"

---

guardrails:

  - "no external posting required"
  - "no escalation unless risk changes"
  - "no marketing tone"
  - "no subreddit violations"

---

success_criteria:

  - "schema valid"
  - "execution completes"
  - "artifact >500 bytes"
  - "reflection file created"
  - "next_prompt file created"
  - "audit trail complete"

---

completion:

  report:
    include:
      - "task_id"
      - "execution_time"
      - "artifact_paths"
      - "best_comment"
      - "weakest_comment"
      - "next_cycle_rules"
      - "PASS / FAIL"
```

---

## EXECUTION PROTOCOL

### Step 1: Submit Task to FLOW

Convert the YAML spec to JSON and submit:

```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "pc_reddit_cycle_v1_1_0",
    "created_at": "2025-05-04T07:00:00Z",
    "source": "production",
    "title": "Prompting Circumstance — Reddit Growth Cycle + Reflection",
    "goal": "Execute Reddit content cycle, score outputs via reflection loop, generate improved prompting rules for next cycle",
    "task_type": "content_prep",
    "risk_tier": "medium",
    "preferred_owner": "hermes",
    "output_required": "pc_reddit_cycle_v1_1_0.md"
  }'
```

**Expected response:**
```json
{
  "status": "accepted",
  "job_id": "pc_reddit_cycle_v1_1_0_[UUID]",
  "owner": "hermes",
  "queue": "flow:hermes:jobs",
  "message": "Task routed to hermes queue"
}
```

**Capture this job_id.** You'll use it for all subsequent queries.

---

### Step 2: Monitor Queue Transitions

Run this command every 2 seconds until completion:

```bash
curl http://localhost:18000/v1/intake/queues/status | jq .queues.hermes
```

Expected sequence:
```
[Initial] hermes: 0
[After submit] hermes: 1          (task queued)
[5 sec] hermes: 0                 (task picked up, now active)
[15 sec] hermes: 0                (task completed, removed from queue)
```

**Record exact timestamps for each transition.**

---

### Step 3: Monitor Execution (Watch Worker Logs)

While task is executing:

```bash
docker logs flow-hermes-worker --follow --tail=50 | grep -i "pc_reddit_cycle_v1_1_0"
```

You should see:
- Task dequeue message
- Step 1: Generate content (OpenRouter call)
- Step 5: Reflection/scoring logic
- Step 6: Prompt update generation
- Task completion

**Record any errors or unexpected behavior.**

---

### Step 4: Verify Audit Trail (All 6 Steps Tracked)

After task completes, query audit_logs:

```bash
psql -c "
  SELECT 
    event_type,
    created_at,
    description,
    event_data
  FROM audit_logs 
  WHERE job_id = '[YOUR_JOB_ID]'
  ORDER BY created_at
;" 
```

**Expected audit events (minimum 4, could be 6+ if each step is tracked):**
- `job_submitted` (task accepted at intake)
- `job_queued` (moved to hermes queue)
- `job_started` (worker picked it up)
- `job_completed` (all 6 steps finished)

**If you see more events (step_1_generate, step_5_reflection, step_6_learning), that's even better — means detailed tracking.**

---

### Step 5: Verify Artifact Files Were Created

Check all three output files exist and contain content:

```bash
# File 1: Main output (content generation)
ls -lah /state/artifacts/pc_reddit_cycle/output.md
cat /state/artifacts/pc_reddit_cycle/output.md | head -50

# File 2: Reflection scores and analysis
ls -lah /state/artifacts/pc_reddit_cycle/reflection.md
cat /state/artifacts/pc_reddit_cycle/reflection.md | head -50

# File 3: Improved prompting rules for next cycle
ls -lah /state/artifacts/pc_reddit_cycle/next_prompt.md
cat /state/artifacts/pc_reddit_cycle/next_prompt.md | head -50
```

**Verify:**
- All 3 files exist ✓
- Each file >500 bytes ✓
- Content is real (not placeholder) ✓
- Reflection file contains scores (clarity, usefulness, authenticity, upvote potential) ✓
- Next_prompt file contains actionable improvements ✓

---

### Step 6: Query Job Record

```bash
psql -c "
  SELECT 
    job_id,
    owner,
    status,
    created_at,
    started_at,
    completed_at,
    result_pointer,
    EXTRACT(EPOCH FROM (completed_at - started_at)) as execution_seconds
  FROM job_records 
  WHERE job_id = '[YOUR_JOB_ID]'
;"
```

**Verify:**
- `status: completed` ✓
- Execution time under 20 seconds ✓ (content gen + reflection + learning is more complex than v1.0.0)
- `result_pointer` points to actual artifact ✓

---

## COMPARATIVE ANALYSIS (v1.0.0 vs v1.1.0)

After v1.1.0 completes, answer these questions:

**Execution Performance:**
- v1.0.0 time: 6.75 seconds
- v1.1.0 time: ? seconds
- Delta: ? (expect +5-10 seconds for reflection + learning)
- Acceptable? Yes if under 20s

**Content Quality:**
- v1.0.0: 3 comments, 1 post (no scoring)
- v1.1.0: Same 3 comments, 1 post, NOW WITH SCORES
  - Did reflection loop run? (files exist?)
  - Best comment score: ? (should be highest)
  - Weakest comment score: ? (should be lowest)
  - Score distribution: range 1-10 or clustered?

**Learning Loop:**
- Did next_prompt.md file generate? ✓
- Does it contain actionable improvements? (read the file)
- Are improvements specific ("reduce buzzwords") or vague ("be better")?
- Would following these rules produce better content?

**Audit Trail:**
- v1.0.0: 4 events (submitted, queued, started, completed)
- v1.1.0: ? events (same 4, or more?)
- Did audit capture reflection step? ✓
- Did audit capture learning step? ✓

---

## DELIVERABLE: Drift Assessment Report

After completing all steps above, create a report with these sections:

### Section 1: Task Metadata
```
Task ID: pc_reddit_cycle_v1_1_0
Job ID: [captured from API response]
Owner: hermes
Risk Tier: medium
Status: PASS or FAIL
Execution Time: [seconds]
```

### Section 2: Execution Summary
```
Step 1 (Generate): ✓ PASS — 3 comments + 1 post generated
Step 2 (Queue): ✓ PASS — submitted to FLOW successfully
Step 3 (Lifecycle): ✓ PASS — pending → active → completed in [X] seconds
Step 4 (Artifact): ✓ PASS — output.md written, [X] bytes
Step 5 (Reflection): ✓ PASS — reflection.md created with scores
Step 6 (Learning): ✓ PASS — next_prompt.md with improvements
```

### Section 3: Content Quality (Reflection Loop Results)
```
Best Comment:
  - Content: [excerpt]
  - Combined Score: [X]/40
  - Why it scored high: [from reflection analysis]

Weakest Comment:
  - Content: [excerpt]
  - Combined Score: [X]/40
  - Why it scored low: [from reflection analysis]

Score Distribution:
  - Clarity scores: [range]
  - Usefulness scores: [range]
  - Authenticity scores: [range]
  - Upvote potential scores: [range]
```

### Section 4: Learning Loop Results (Prompt Improvements)
```
Generated Improvements:
  - What to do more of:
    1. [specific action from next_prompt.md]
    2. [specific action]
  - What to avoid:
    1. [specific avoidance from next_prompt.md]
    2. [specific avoidance]

Recommended Adjustments for Next Cycle:
  - Tone shift: [from next_prompt.md]
  - Structure tweak: [from next_prompt.md]
  - Angle refinement: [from next_prompt.md]
```

### Section 5: Comparative Analysis (v1.0.0 vs v1.1.0)
```
Performance Delta:
  - v1.0.0 execution: 6.75 seconds
  - v1.1.0 execution: [X] seconds
  - Increase: [X]% (acceptable if <150%)

Capability Delta:
  - v1.0.0: Generate content only
  - v1.1.0: Generate + score + learn
  - Assessment: [describes what new capability means]

Quality Trend:
  - Did reflection scores improve concept execution?
  - Did learning loop generate actionable improvements?
  - Is the system improving itself?
```

### Section 6: Audit Trail Verification
```
Events Recorded:
  - job_submitted: ✓ [timestamp]
  - job_queued: ✓ [timestamp]
  - job_started: ✓ [timestamp]
  - job_completed: ✓ [timestamp]
  - [any additional step events]: ✓ [timestamp]

Timing Validation:
  - Submit → Queue: [ms] ✓
  - Queue → Start: [ms] ✓
  - Start → Complete: [seconds] ✓
```

### Section 7: Artifacts Delivered
```
✓ /state/artifacts/pc_reddit_cycle/output.md — [X] bytes
✓ /state/artifacts/pc_reddit_cycle/reflection.md — [X] bytes
✓ /state/artifacts/pc_reddit_cycle/next_prompt.md — [X] bytes
✓ /state/artifacts/pc_reddit_cycle/metadata.json — [X] bytes
```

### Section 8: Success Criteria Checklist
```
✓ Schema valid — HTTP 200 response
✓ Execution completes — status: completed in database
✓ Artifact >500 bytes — all 3 files meet requirement
✓ Reflection file created — scores and analysis present
✓ Next_prompt file created — improvements documented
✓ Audit trail complete — all 4+ events recorded
✓ No escalation — task completed as medium risk
✓ No external posting — simulation only, as designed
```

### Section 9: Final Decision
```
RESULT: PASS or FAIL

If PASS:
  - FLOW can execute complex workflows (6 steps)
  - Reflection loop provides actionable intelligence
  - Learning loop generates improvements
  - System demonstrates drift management capability
  - Ready for: [next iteration recommendations]

If FAIL:
  - Which step failed? [step number and error]
  - Error message: [exact error]
  - Impact: [what does this block]
  - Recommendation: [fix required before next attempt]
```

---

## CONSTRAINTS & RULES

❌ **DO NOT:**
- Skip any of the 6 steps
- Manually modify artifact files (let the system create them)
- Post content externally (simulation only)
- Escalate task unless genuinely high-risk
- Deploy before reporting all results

✅ **DO:**
- Run steps sequentially
- Capture exact timestamps
- Verify all 3 output files
- Compare with v1.0.0 results
- Report anomalies immediately

---

## CRITICAL SUCCESS FACTORS

This task succeeds if:

1. **All 6 steps execute** without error
2. **Reflection loop produces scores** (not empty)
3. **Learning loop generates rules** (not placeholder)
4. **Audit trail tracks everything** (4+ events)
5. **Artifacts persist** (all 3 files readable)
6. **Comparative analysis shows improvement** (not degradation)

**If any of these fail, that's the blocker to report.**

---

## TIMELINE & EXPECTATIONS

- **Submit to FLOW:** 1 minute
- **Execution time:** 15-25 seconds (v1.0.0 was 6.75s, adding reflection/learning)
- **Monitoring:** 2-3 minutes
- **Artifact verification:** 2-3 minutes
- **Report writing:** 10-15 minutes

**Total: ~30-45 minutes from submission to complete report**

---

## QUESTIONS TO ANSWER IF ISSUES ARISE

1. At which step did execution fail?
2. What was the exact error message?
3. Did audit events record before failure?
4. Are partial artifacts present?
5. What was the last successful step?

**Report these before asking for help.**

---

## HANDOFF COMPLETE

**For Cursor:**

Execute this drift assessment task (v1.1.0) using the protocol above.

Report back with:
- Execution time
- All 3 artifact files (or summaries)
- Best/weakest comment scores
- Generated improvements for next cycle
- Comparative analysis vs v1.0.0
- Final PASS/FAIL with evidence

This is production work. Execute sequentially, capture all data, report comprehensively.

---

**Prepared by:** Gordon (Infrastructure Authority)  
**For:** Cursor (Development Execution)  
**Date:** 2025-05-04  
**Authority:** Full execution delegation
