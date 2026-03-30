# FLOW Agent OS - Complete Knowledge Base for NotebookLM

**Created:** 2026-02-28  
**Purpose:** Leverage library for TransformBy10x AI agent training  
**Source:** Complete FLOW Agent OS build session

---

## TABLE OF CONTENTS

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Universal Role Anchor (Prompt Engineering)](#universal-role-anchor)
5. [Execution Prompt Architecture](#execution-prompt-architecture)
6. [Cost Discipline](#cost-discipline)
7. [Risk Tiers & Routing](#risk-tiers--routing)
8. [Gamma Safety Protocol](#gamma-safety-protocol)
9. [Task Envelope Schema](#task-envelope-schema)
10. [Build-Mode Philosophy](#build-mode-philosophy)
11. [Deployment Guide](#deployment-guide)
12. [Integration Points](#integration-points)

---

## SYSTEM OVERVIEW

**Product:** FLOW Agent OS  
**Created by:** TransformBy10x.ai  
**Purpose:** Multi-agent artifact execution with cost optimization and safety gates

### What It Is

FLOW Agent OS is build-mode infrastructure. Task envelopes go in, deployed artifacts come out. Zero iteration, zero babysitting, zero assistant mode.

### Core Features

1. **One-Shot Execution** - Envelope → artifact with no human iteration
2. **Build-Mode Philosophy** - Agents build, not assist
3. **Cost Optimization** - 93.7% reduction vs. all-Opus routing ($6.60 vs $105 per 1K tasks)
4. **Gamma Safety** - Two-pass review for critical tasks (deploy, DNS, secrets, DB)
5. **Proof in Production** - Self-hosted, built using itself

### The Numbers

- **Cost reduction:** 93.7% ($2,952/month savings)
- **Routing time:** ~5-10 seconds
- **Executors:** 5 (router + 3 agents + orchestrator)
- **Risk tiers:** 3 (Alpha/Beta/Gamma)
- **Gamma passes:** 2 (ChatGPT generation → Claude review)

---

## ARCHITECTURE

### Pipeline Flow

```
Task Envelope (pending/)
    ↓
Router (validates, enriches, routes to active/)
    ↓
Executor (agent-specific: claude/gemini/chatgpt)
    ↓
[If Gamma] Gamma Orchestrator (two-pass review)
    ↓
Artifact Written + Envelope → completed/
    ↓
Events Logged (events.jsonl)
    ↓
[If Gamma] Human Approval Required
```

### Component Map

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| Router | `router.py` v0.2.0 | Task validation & routing | ✅ Production |
| Claude Executor | `claude_executor.py` v1.0.0 | Code, content, docs | ✅ Production |
| Gemini Executor | `gemini_executor.py` v1.0.0 | Visual analysis | ✅ Production |
| ChatGPT Executor | `chatgpt_executor.py` v1.0.0 | Architecture, Gamma Pass 1 | ✅ Production |
| Gamma Orchestrator | `gamma_orchestrator.py` v1.0.0 | Two-pass safety review | ✅ Production |
| Gemini Worker | `gemini_worker.py` v0.3.0 | OpenRouter API integration | ✅ Production |

### Directory Structure (Per Project)

```
projects/my-project/
├── tasks/
│   ├── pending/          # Drop tasks here
│   ├── active/           # Router moves them here
│   ├── intermediate/     # Gamma Pass 1 → Pass 2 handoff
│   ├── completed/        # Finished tasks
│   ├── blocked/          # Failed validation or API errors
│   └── escalated/        # Gamma rejections needing human review
├── status/               # Current status per task
├── events.jsonl          # Event log (append-only)
└── metadata.json         # Project metadata
```

---

## CORE COMPONENTS

### 1. Router (v0.2.0)

**Location:** `~/.openclaw/state/_os/router.py`

**Responsibilities:**
- Watches `projects/*/tasks/pending/` directories
- Validates task envelope schema
- Detects DSM keywords (deploy, DNS, database, secrets) → auto-escalates Beta to Gamma
- Enforces Gamma constraints (two-pass, rollback, human approval)
- Enriches task with routing metadata and cost budget
- Moves task to `active/`
- Logs events to `events.jsonl`

**Routing Logic:**
```python
EXECUTOR_MAP = {
    "reputation": "claude",               # Alpha (public-facing)
    "time_loss": "claude",                # Beta (internal ops) - default, can route to gemini
    "downtime_security_money": "chatgpt"  # Gamma (critical, Pass 1)
}
```

**DSM Keywords (Auto-Escalation):**
```python
DSM_KEYWORDS = [
    "deploy", "deployment", "production", "prod",
    "dns", "database", "db", "migration", "migrate",
    "secret", "secrets", "api_key", "apikey", "credential",
    "ssl", "certificate", "firewall",
    "infra", "infrastructure", "server", "hosting",
    "supabase", "vercel", "stripe_webhook"
]
```

**Gamma Constraints (Always Enforced):**
```python
GAMMA_CONSTRAINTS = {
    "two_pass_required": True,
    "diff_required": True,
    "rollback_required": True,
    "human_approval_required": True
}
```

### 2. Claude Executor (v1.0.0)

**Location:** `~/.openclaw/state/_os/claude_executor.py`

**Handles:**
- Script generation
- Blog posts / content
- Operational documentation

**Cost:** ~$0.03 per task (Claude Sonnet 4.5)

**Prompt Engineering:**
- Loads Universal Role Anchor template
- Enforces execution verbs (Generate/Produce/Assemble)
- "Generate this as if it will be pasted directly into a live product. No explanations."
- Artifact-first framing

**Validation:**
- Shellcheck for bash scripts
- JSON parse for JSON artifacts
- Em dash detection for content
- Custom validation via `outputs.validation` field

**Output:**
- Writes artifact to `outputs.destination`
- Creates .bak backup if file exists
- Makes scripts executable (chmod 755)
- Moves envelope to `completed/`
- Logs cost, usage, model to events.jsonl

### 3. Gemini Executor (v1.0.0)

**Location:** `~/.openclaw/state/_os/gemini_executor.py`

**Handles:**
- Visual analysis (screenshots, mockups, UI)
- Image-based tasks
- Design review

**Cost:** ~$0.001 per task (Gemini Flash 1.5) — **200x cheaper than Claude/ChatGPT**

**Uses:** `gemini_worker.py` module (OpenRouter API)

**Output Formats:**
- JSON (structured analysis with confidence scores)
- Markdown (formatted report with findings/recommendations)

**Analysis Schema:**
```python
{
    "analysis_type": "ui_review",
    "confidence": 0.85,
    "findings": ["Finding 1", "Finding 2"],
    "recommendations": ["Recommendation 1"],
    "timestamp": "2026-02-28T10:30:00Z"
}
```

### 4. ChatGPT Executor (v1.0.0)

**Location:** `~/.openclaw/state/_os/chatgpt_executor.py`

**Handles:**
- Architecture design
- System specifications
- Gamma Pass 1 (critical task generation)

**Cost:** ~$0.02 per task (GPT-5.2 or GPT-4 Turbo)

**Gamma Pass 1 Behavior:**
- Detects `risk_tier: gamma` + `pass: 1`
- Generates artifact with inline safety comments
- Documents rollback steps
- Includes validation logic
- Moves to `intermediate/` (not `completed/`)
- Sets `status: awaiting_review`, `next_pass: 2`, `next_routed_to: claude`

### 5. Gamma Orchestrator (v1.0.0)

**Location:** `~/.openclaw/state/_os/gamma_orchestrator.py`

**Watches:** `projects/*/tasks/intermediate/` for `status: awaiting_review`

**Triggers:** Claude review (Pass 2) for Gamma tasks

**Review Checklist (6 Criteria):**
1. **Correctness:** Does it accomplish the stated task?
2. **Safety:** Data loss, downtime, security risks?
3. **Rollback:** Can we undo if it breaks? Is the plan clear?
4. **Validation:** Can we test before full deployment?
5. **Dependencies:** Are external dependencies handled?
6. **Secrets:** No hardcoded credentials, API keys?

**Claude Returns:**
```json
{
  "approved": true,
  "correctness": "pass",
  "safety": "pass",
  "rollback": "pass",
  "validation": "pass",
  "dependencies": "pass",
  "secrets": "pass",
  "findings": ["Finding 1"],
  "recommendations": ["Recommendation 1"],
  "approval_token": "APPROVED"
}
```

**Outcomes:**
- **APPROVED** → moves to `completed/` with `human_approval_required: true`
- **REJECTED** → moves to `escalated/` with rejection reasons

---

## UNIVERSAL ROLE ANCHOR

**Location:** `~/PROJECTS/_OS/03-Prompts/00-System/UNIVERSAL_ROLE_ANCHOR.md`

### Role Definition

Act as an operator-level systems architect and execution partner.

Produce concrete, deployable business assets.

Do not explain concepts or brainstorm ideas unless explicitly asked.

**If an output cannot be directly stored as an artifact in a business workspace, rewrite it until it can.**

### Execution Verbs

**Approved:**
- Generate
- Produce
- Rewrite
- Structure
- Condense
- Translate
- Assemble

**Banned:**
- Explain
- Discuss
- Brainstorm
- Talk about

### Prompt Framing

All prompts must include:

> "Generate this as if it will be pasted directly into a live product. No explanations."

### First Artifact Standards (6-Point Checklist)

Every task envelope must pass:

1. **Artifact Identity** - Type declared (SOP/Workflow/Page/Schema/etc.)
2. **Workspace Ownership** - Destination path specified
3. **Persistence Test** - Destination valid, survives session close
4. **Input/Output Clarity** - Exact data flow defined
5. **Next Action Linkage** - Artifact enables trigger/action/decision
6. **No Human Memory Dependency** - All context in envelope (no "remember to", "decide later", "use judgment")

### Output Modes

1. **Marketing Surface** - Restrained, declarative, name tension, consequences not promises
2. **System Interface Copy** - Factual, state changes, no metaphors
3. **Operational Documentation** - Executable steps, zero assumed context
4. **Internal Strategy** - Direct, opinionated, name constraints/failures

---

## EXECUTION PROMPT ARCHITECTURE

**Location:** `~/PROJECTS/_OS/03-Prompts/00-System/EXECUTION_PROMPT_ARCHITECTURE.md`

### Template Hierarchy

**Minimal (Beta tier, single-agent):**
```markdown
## Task: [One-line description]
**Risk tier:** Beta
**Model:** Gemini Flash 1.5 (cost-optimized)

**Context:**
- [What you need to know]

**Execute:**
[Clear instruction]

**Artifact:**
[What you'll produce]
```

**Standard (Alpha tier, public-facing):**
```markdown
## Task: [One-line description]
**Risk tier:** Alpha
**Model:** Gemini Flash 1.5 (visual-first)
**Review required:** Yes

**Context:**
- Audience: [who sees this]
- Voice: [TB10X/Erik personal/etc.]

**Execute:**
[Clear instruction with constraints]

**Artifact:**
- Format: [markdown/HTML/etc.]
- Required elements: [CTAs, links, images]

**Success criteria:**
- [ ] On-brand voice
- [ ] No em dashes, no qualifiers
```

**Maximum (Gamma tier, two-pass):**
```markdown
## Task: [One-line description]
**Risk tier:** Gamma
**Two-pass mandatory:** ChatGPT → Claude
**Human approval:** REQUIRED

**Context:**
- Current state: [what exists]
- Desired state: [what we want]
- Rollback plan: [how to undo]

**Pass 1 (ChatGPT):**
Generate with inline safety comments.

**Pass 2 (Claude):**
Review for correctness, safety, rollback.

**Artifact:**
- Type: [code/config/SQL/etc.]
- Backup: [where old version saved]

**Execution checklist:**
- [ ] Artifact generated (Pass 1)
- [ ] Review complete with APPROVED token (Pass 2)
- [ ] Human approval received
```

### Context Inclusion Rules

**Always include:**
- Risk tier
- Model selection (with cost justification if expensive)
- Artifact specification
- Success criteria (checklist format)

**Include when applicable:**
- Audience/platform (Alpha tier)
- Voice guidelines (public-facing)
- Dependencies (Gamma tier)
- Rollback plan (Gamma mandatory)

**Never include:**
- Unnecessary backstory
- Emotional framing
- Multiple interpretations
- Vague success criteria

### Platform-Specific Formatting

**Discord:**
- No markdown tables → use bullet lists
- Multiple links → wrap in `<>` to suppress embeds
- Code blocks with language specifier

**WhatsApp:**
- No headers → use **bold** or CAPS
- No markdown tables → bullet lists only
- Plain URLs (auto-link)

**Telegram:**
- Markdown supported (keep simple)
- Inline buttons via `message` tool
- Code blocks work

**Email (Himalaya):**
- Plain text default
- Structure with whitespace
- Spell out links clearly

---

## COST DISCIPLINE

**Location:** `~/.openclaw/state/_shared/COST_DISCIPLINE.md`

### The Problem

**Before FLOW Agent OS:**
- All tasks routed to Claude Opus
- Cost: $105/day for 1000 tasks
- Monthly: $3,150
- No cost awareness in routing

### The Solution

**Cost-first routing:**
- Default to Gemini Flash 1.5 (~200x cheaper)
- Escalate to expensive models only when necessary
- Cost is first-class routing criterion (not optional)

### Model Pricing (Estimates)

| Model | Input | Output | Avg Task Cost |
|-------|-------|--------|---------------|
| Gemini Flash 1.5 | $0.075/1M | $0.30/1M | **$0.001** |
| Claude Sonnet 4.5 | $3/1M | $15/1M | $0.03 |
| GPT-5.2 / GPT-4 Turbo | $10/1M | $30/1M | $0.02 |

### Routing Defaults

**Beta lane (ops/automation/execution):**
- **Default:** Gemini ($0.001/task)
- **Escalate to:** Claude when complex code/content needed
- **Escalate to:** ChatGPT when architecture required

**Alpha lane (reputation/public):**
- **Default:** Gemini for visual-first tasks
- **Prefer:** Claude for content requiring Erik's voice or high quality

**Gamma lane (critical):**
- **Pass 1:** ChatGPT ($0.02)
- **Pass 2:** Claude ($0.03)
- **Total:** $0.05/task (justified for safety)

### Impact

**After optimization:**
- Gemini: 800 tasks × $0.001 = $0.80
- Claude: 150 tasks × $0.03 = $4.50
- ChatGPT: 40 tasks × $0.02 = $0.80
- Gamma: 10 tasks × $0.05 = $0.50
- **Total:** $6.60/day → $198/month

**Savings:** $2,952/month (93.7% reduction)

### Enforcement

Cost discipline is enforced at the routing layer, not optional.

Router checks cost budget before routing. Executors log actual cost to events.jsonl.

---

## RISK TIERS & ROUTING

**Location:** `~/.openclaw/AGENT_ROUTING_POLICY.md`

### Prime Directive

**Route by risk first. Then by cost-optimized capability.**

Capability never overrides risk tier.

Cost discipline is enforced, not optional.

### Risk Tier Definitions

| Tier | Risk Type | Examples | Model Default |
|------|-----------|----------|---------------|
| **Alpha** | Reputation | Blog posts, client emails, public docs, marketing copy | Gemini (visual-first) or Claude (voice-critical) |
| **Beta** | Time-loss | Scripts, automation, internal tools, data processing, visual analysis | **Gemini** (cost-optimized) |
| **Gamma** | Downtime/Security/Money | Production deploys, DNS changes, API keys, database migrations | ChatGPT → Claude (two-pass) |

### Routing Rules

1. **Risk tier determines the lane** (hard rule, non-negotiable)
2. **Cost determines the model within capability tier** (prefer cheaper when capable)
3. **Capability matrix determines model fallback** (escalate only when necessary)
4. **If risk is ambiguous:** escalate one tier
5. **If capability is ambiguous:** stay in-lane, use cheapest capable model
6. **Anything touching deploy/secrets/DNS/DB:** Gamma + two-pass mandatory

### DSM Auto-Escalation

If a Beta task contains DSM keywords (deploy, database, secrets, etc.), router automatically escalates to Gamma.

This prevents developers from accidentally bypassing safety review.

### Escalation Paths

- **Alpha concern?** Flag for human review before publishing
- **Beta blocked?** Escalate to ChatGPT or Claude for architecture decision
- **Gamma failure?** Stop. Do not proceed. Alert human immediately.

---

## GAMMA SAFETY PROTOCOL

**Why Gamma Exists:**
Critical tasks (deploy, DNS, secrets, DB) require two-pass review + human approval to prevent:
- Data loss
- Service downtime
- Security breaches
- Irreversible changes without rollback

### Two-Pass Flow

**Pass 1 (Generation):**
1. ChatGPT receives task envelope
2. Generates artifact with inline safety comments
3. Documents rollback steps
4. Includes validation logic
5. Writes to `intermediate/` with `status: awaiting_review`

**Pass 2 (Review):**
1. Gamma Orchestrator detects task in `intermediate/`
2. Triggers Claude review with 6-point checklist
3. Claude evaluates artifact for safety/correctness
4. Returns structured JSON with approval token
5. If APPROVED → moves to `completed/` (human approval required)
6. If REJECTED → moves to `escalated/` with rejection reasons

**Human Gate:**
1. Review completed envelope + artifact + both agent evaluations
2. If approved: deploy manually
3. If rejected: move back to `pending/` with feedback or abandon

### Safety Checklist (6 Criteria)

Claude evaluates Pass 1 artifact against:

1. **Correctness** - Does it accomplish the stated task?
2. **Safety** - Are there data loss, downtime, or security risks?
3. **Rollback** - Can we undo this if it breaks? Is the plan clear?
4. **Validation** - Can we test this before full deployment?
5. **Dependencies** - Are all external dependencies handled?
6. **Secrets** - No hardcoded credentials, API keys, or secrets?

Each criterion must return: `pass`, `fail`, or `concern`

### Approval Response Schema

```json
{
  "approved": true,
  "correctness": "pass",
  "safety": "pass",
  "rollback": "pass",
  "validation": "pass",
  "dependencies": "pass",
  "secrets": "pass",
  "findings": [
    "Rollback plan is well-documented",
    "Validation steps are clear"
  ],
  "recommendations": [
    "Test in staging before production"
  ],
  "approval_token": "APPROVED"
}
```

**If approved = false or approval_token = "REJECTED":**
- Task moves to `escalated/`
- Rejection reasons logged in `findings`
- Human review required before retry

### Cost of Gamma

**Pass 1 (ChatGPT):** ~$0.02  
**Pass 2 (Claude):** ~$0.03  
**Total:** ~$0.05 per Gamma task

**Justified because:**
- Prevents costly mistakes (downtime = $$$)
- Human time savings (catch errors before deploy)
- Safety compliance (two independent agents + human)

---

## TASK ENVELOPE SCHEMA

### Required Fields

```json
{
  "task_id": "unique-identifier",
  "timestamp": "2026-02-28T10:30:00Z",
  "risk_tier": "beta",
  "task_type": "script_generation",
  "description": "What to build"
}
```

### Inputs (Task-Specific)

```json
{
  "inputs": {
    "key1": "value1",
    "key2": "value2",
    "image_path": "/path/to/image.png",
    "database": "production_db"
  }
}
```

### Outputs (Artifact Specification)

```json
{
  "outputs": {
    "artifact_type": "bash_script",
    "destination": "~/PROJECTS/EVA-PARADIS/scripts/backup.sh",
    "validation": "shellcheck"
  }
}
```

### Optional Fields

```json
{
  "model_preference": "gemini",
  "cost_limit_usd": 0.50,
  "deadline": "2026-03-01T00:00:00Z",
  "depends_on": ["other-task-id"]
}
```

### Complete Example (Beta Task)

```json
{
  "task_id": "backup-script-001",
  "timestamp": "2026-02-28T10:30:00Z",
  "risk_tier": "beta",
  "task_type": "script_generation",
  "description": "Generate backup script for Eva Paradis database",
  "inputs": {
    "source": "supabase://eva-paradis",
    "destination": "/backups/eva-paradis",
    "schedule": "daily 02:00 UTC"
  },
  "outputs": {
    "artifact_type": "bash_script",
    "destination": "~/PROJECTS/EVA-PARADIS/scripts/backup.sh",
    "validation": "shellcheck + dry-run test"
  }
}
```

### Complete Example (Gamma Task)

```json
{
  "task_id": "deploy-production-001",
  "timestamp": "2026-02-28T10:30:00Z",
  "risk_tier": "gamma",
  "task_type": "deployment_script",
  "description": "Deploy Eva Paradis app to Vercel production",
  "inputs": {
    "service": "eva-paradis",
    "environment": "production",
    "branch": "main",
    "vercel_project_id": "prj_abc123"
  },
  "outputs": {
    "artifact_type": "bash_script",
    "destination": "~/PROJECTS/EVA-PARADIS/scripts/deploy-prod.sh",
    "validation": "dry-run + staging test"
  }
}
```

Router will automatically add:
```json
{
  "two_pass_required": true,
  "diff_required": true,
  "rollback_required": true,
  "human_approval_required": true,
  "pass": 1,
  "routed_to": "chatgpt"
}
```

---

## BUILD-MODE PHILOSOPHY

### What Is Build-Mode?

**Build-mode** is infrastructure for one-shot execution.

Agents don't assist. They build.

Task envelope goes in. Deployed artifact comes out. Zero iteration, zero babysitting, zero conversation loops.

### Core Principles

1. **Artifacts over ideas** - Deliverables, not discussions
2. **Outputs over explanations** - Systems, not sessions
3. **Operator over assistant** - Execution partner, not chatbot
4. **One-shot over iteration** - Right the first time
5. **Philosophy over technology** - TB10X thesis drives infrastructure

### What One-Shot Means

**Not iteration:**
- Task → artifact → "let me know if you need changes" ❌

**One-shot:**
- Task → artifact → deployed ✅

**The system decides:**
- Model selection (cost-optimized)
- Validation method (artifact-type specific)
- Routing path (risk tier + capability)
- Review process (single-pass or Gamma two-pass)

**Human involvement:**
- Submit task envelope
- Review completed Gamma artifacts before deploy
- Nothing else required

### Proof in Production

FLOW Agent OS was built using FLOW Agent OS.

The executors were generated as artifacts. The documentation was generated as artifacts. The landing page was generated as an artifact.

Self-hosting. Self-improving. Live on real infrastructure.

**This is the TB10X thesis made real:**

Most people operate at 10% capacity. AI is the lever. But only with the right context architecture.

FLOW Agent OS is that architecture.

---

## DEPLOYMENT GUIDE

### Prerequisites

- Python 3.9+
- API keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` (OpenRouter)
- tmux (for background execution)
- Git (for version control)

### Installation

**1. Clone FLOW Agent OS:**
```bash
# Repository structure already exists
cd ~/.openclaw/state/_os
```

**2. Set API keys:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# For Gemini (via OpenRouter)
echo "GEMINI_API_KEY=sk-or-..." > ~/.openclaw/state/_os/.env.gemini
echo "GEMINI_MODEL=google/gemini-flash-1.5" >> ~/.openclaw/state/_os/.env.gemini
```

**3. Install Python dependencies:**
```bash
pip install anthropic openai
```

### Testing

**End-to-end test:**
```bash
~/.openclaw/state/_os/test-e2e.sh
```

This creates a test project, submits Beta and Gamma tasks, and validates the full pipeline.

**Expected output:**
- Tasks routed correctly
- Executors generate artifacts
- Gamma two-pass flow completes
- Events logged to `events.jsonl`
- Artifacts written to destination paths

### Starting the System

**Launch all executors in tmux:**
```bash
~/.openclaw/state/_os/start-all.sh
```

This starts 5 background processes:
- `flow-router` - Task routing
- `flow-claude` - Claude executor
- `flow-gemini` - Gemini visual analysis
- `flow-chatgpt` - ChatGPT architecture
- `flow-gamma` - Gamma orchestrator

**Check status:**
```bash
tmux list-sessions | grep flow
```

**Attach to a session:**
```bash
tmux attach -t flow-router
```
(Press `Ctrl+b` then `d` to detach)

**View logs in real-time:**
```bash
# Router logs
tmux attach -t flow-router

# Claude executor logs
tmux attach -t flow-claude

# Gamma orchestrator logs
tmux attach -t flow-gamma
```

### Stopping the System

```bash
~/.openclaw/state/_os/stop-all.sh
```

### Submitting Tasks

**1. Create project (if needed):**
```bash
~/.openclaw/state/_os/new-project.sh my-project
```

**2. Create task envelope:**
```bash
cat > ~/.openclaw/state/projects/my-project/tasks/pending/task-001.json <<EOF
{
  "task_id": "task-001",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "risk_tier": "beta",
  "task_type": "script_generation",
  "description": "Generate backup script for database",
  "outputs": {
    "artifact_type": "bash_script",
    "destination": "~/scripts/backup.sh",
    "validation": "shellcheck"
  }
}
EOF
```

**3. Wait for execution:**
- Router picks up task within ~5s
- Executor processes within ~10-30s
- Check `completed/` for finished envelope

**4. Review artifact:**
```bash
cat ~/scripts/backup.sh
```

### Monitoring

**View events:**
```bash
cat ~/.openclaw/state/projects/my-project/events.jsonl | jq
```

**Filter by event type:**
```bash
cat events.jsonl | jq 'select(.event == "task_completed")'
```

**Calculate total cost:**
```bash
cat events.jsonl | jq -s 'map(.cost_usd // 0) | add'
```

**See failures:**
```bash
cat events.jsonl | jq 'select(.event | contains("fail") or contains("block"))'
```

---

## INTEGRATION POINTS

### TB10X Modules

**BizBot (Infrastructure):**
- Use FLOW Agent OS to standardize service delivery
- Generate client assessment reports
- Automate Digital Systems deliverables
- One-shot intake form processing

**BizBuilders (Leverage):**
- Use FLOW Agent OS to scale product delivery
- Generate infrastructure assessments
- Build reusable templates (no custom work per client)
- Ship scalable, sellable assets

**Eva Paradis (Conversion):**
- Use FLOW Agent OS for marketing automation
- Generate social posts, blog content
- Process analytics reports
- Build conversion funnel assets

### Future Integrations

**Notion API:**
- Submit tasks from Notion databases
- Write completed artifacts to Notion pages

**GitHub Actions:**
- Trigger tasks on PR merge
- Auto-generate documentation
- Deployment automation

**Telegram Bot:**
- Submit tasks via chat message
- Receive completion notifications
- Human approval via inline buttons

**Supabase:**
- Store task envelopes in database
- Log events to Supabase table
- Trigger tasks from database events

---

## BUILD SESSION SUMMARY

**Date:** 2026-02-28  
**Duration:** Single session  
**Trigger:** "how do we execute artifacts?"

### What Was Built

1. **Claude Executor** (v1.0.0) - Code, content, docs generation
2. **Gemini Executor** (v1.0.0) - Visual analysis (200x cheaper)
3. **ChatGPT Executor** (v1.0.0) - Architecture + Gamma Pass 1
4. **Gamma Orchestrator** (v1.0.0) - Two-pass safety review
5. **Management Scripts** - start-all.sh, stop-all.sh, test-e2e.sh
6. **Documentation** - 4 canonical reference files
7. **Deliverable Artifacts** - FLOW Agent OS landing page, BizBot intake form

### What Was Learned

**Erik's feedback:** "looking at a markdown file instead of a layout, pdf or .html file is pointless"

**The correction:** Artifacts must have independent value. Documentation about the system isn't an artifact. Deployable HTML pages are artifacts.

**Build-mode positioning:** FLOW Agent OS isn't a "multi-agent execution pipeline" (technical). It's "build-mode execution, one-shot delivery, proof of philosophy in production" (philosophy-driven).

### Cost Impact

**Before:** $105/day ($3,150/month) routing everything to Opus  
**After:** $6.60/day ($198/month) with cost-optimized routing  
**Savings:** $2,952/month (93.7% reduction)

### The Philosophy

Technology serves philosophy. FLOW Agent OS is the TB10X thesis made infrastructure:

**Thesis:** Most people operate at 10% capacity. AI is the lever. But only with the right context architecture.

**Proof:** FLOW Agent OS. Build-mode execution. One-shot delivery. Self-hosted, self-improving, live on real infrastructure.

---

**This knowledge base is optimized for NotebookLM ingestion. Upload to create a leverage library for AI agent training.**

**Created by:** DOC (Doctor Open Claw)  
**Date:** 2026-02-28  
**Source:** TransformBy10x.ai
