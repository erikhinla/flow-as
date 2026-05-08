# FLOW Agent AS — Marketing Job Workflow
### A complete reference for understanding how a marketing task moves through the FLOW autonomous agent system

---

## What is FLOW Agent AS?

FLOW Agent AS is an autonomous agent operating system. It receives work requests (called **task envelopes**), validates them, routes them to the right AI agent, executes the work using a large language model, and returns a finished artifact. Think of it as a digital agency back-office that runs 24/7.

The system is live on a VPS server. It currently consists of:
- A REST API (BizBrain Lite) that accepts jobs
- A PostgreSQL database that tracks every job from creation to completion
- A Redis message queue that distributes work to agents
- Three autonomous worker agents (OpenClaw, Hermes, Agent Zero)

---

## The Agents

### OpenClaw
OpenClaw is the routing agent. It does not create content — it reads the job and decides which agent should handle it. It evaluates the task type and risk tier to make that decision.

### Hermes
Hermes is the content and classification agent. It handles:
- Content preparation (writing marketing copy, social posts, email sequences)
- Rewriting and editing existing content
- Skill extraction (learning from past jobs to improve future performance)
- Healthcheck tasks

### Agent Zero
Agent Zero is the implementation agent. It handles:
- Complex multi-step deliverables
- Landing pages and full campaign builds
- Anything that requires synthesis across multiple outputs
- High-risk or high-complexity tasks that need careful execution

---

## The Marketing Job — Step by Step

### Phase 1: Brief and Submission

**Step 1 — Write the brief**
A marketing job starts with a brief. The brief defines:
- What you want (goal): e.g. "Write a 3-part email sequence for a product launch targeting SaaS founders"
- What type of work it is (task_type): e.g. `content_prep`
- How sensitive or risky it is (risk_tier): e.g. `low`
- Who should handle it (preferred_owner): e.g. `hermes`
- What output is needed (output_required): e.g. `true`
- Whether it needs human review (review_required): e.g. `true`

**Step 2 — Send the API request**
The brief is submitted as a structured JSON object to the BizBrain API:

```
POST http://31.220.49.96:18000/v1/intake/task
Header: X-Api-Token: <your token>
```

Example payload for a marketing content job:
```json
{
  "task_id": "a1b2c3d4-0000-0000-0000-000000000001",
  "created_at": "2026-04-29T10:00:00Z",
  "source": "client_portal",
  "title": "Product Launch Email Sequence",
  "goal": "Write a 3-part email sequence for a SaaS product launch targeting founders",
  "task_type": "content_prep",
  "risk_tier": "low",
  "preferred_owner": "hermes",
  "output_required": true,
  "review_required": true,
  "status": "pending"
}
```

---

### Phase 2: Intake and Validation

**Step 3 — Schema validation**
BizBrain Lite receives the job and immediately checks it against the task envelope schema (`task_envelope.schema.json`). Every required field must be present and the values must match the allowed options. If anything is wrong, the API rejects the job and returns a clear error message.

Required fields include: `task_id`, `created_at`, `source`, `title`, `goal`, `task_type`, `risk_tier`, `preferred_owner`, `output_required`, `review_required`, `status`.

**Step 4 — Write to database**
If validation passes, the job is written to the `job_records` table in PostgreSQL. The status is set to `pending`. The system now has a permanent record of this job.

**Step 5 — Return a job ID**
The API immediately returns the unique job ID (UUID) to the caller. The caller can use this ID to check the job status at any time via the queue status API:
```
GET http://31.220.49.96:18000/v1/intake/queues/status
```

---

### Phase 3: Routing

**Step 6 — Read task type**
OpenClaw reads the `task_type` field. For a `content_prep` task, it knows this is writing work and not implementation work.

**Step 7 — Risk check**
OpenClaw reads the `risk_tier`. A `low` risk content job can be handled autonomously without escalation. A `high` risk job triggers an escalation path.

**Step 8 — Assign owner**
Based on task type and risk tier, OpenClaw assigns the job to an owner agent:
- `content_prep` / `rewrite` / `skill_extraction` → **Hermes**
- `implementation` / complex multi-step → **Agent Zero**
- Routing decisions themselves → **OpenClaw**

The preferred_owner from the brief is considered but OpenClaw can override it.

---

### Phase 4: Queue

**Step 9 — Enqueue the job**
The job is pushed into the Redis queue for the assigned owner. The queue key follows the pattern `flow:{owner}:jobs`. For our email sequence job, it goes to `flow:hermes:jobs`. The database status is updated to `queued`.

**Step 10 — Worker waits**
The Hermes worker process (running as a Docker container on the server) is permanently blocked on a `BRPOP` command, meaning it sits idle and waits for jobs to appear on its queue. No polling, no wasted CPU — it wakes up only when there is work.

**Step 11 — Job dequeued**
When the job arrives on the queue, the Hermes worker wakes up, pops the job, reads the job ID, and updates the database status to `active`. The job is now being worked on.

---

### Phase 5: Agent Execution

**Step 12 — Load context**
The agent loads the full task envelope from the database along with any relevant memory or skill records from previous similar jobs. This context is assembled into a prompt.

**Step 13 — LLM call via OpenRouter**
The agent sends the prompt to OpenRouter, which routes it to the appropriate language model:
- GPT-4o for high-quality content with nuance
- Claude for longer structured writing
- Mistral for fast, cost-efficient simpler tasks

For the email sequence, the agent sends a prompt like:
> "You are a B2B SaaS copywriter. Write a 3-part email sequence for a product launch. Email 1: problem-awareness. Email 2: solution reveal. Email 3: urgency CTA. Target audience: SaaS founders. Tone: direct, peer-to-peer."

**Step 14 — Generate output**
The LLM returns the finished content. For a marketing job, this might be:
- Three complete email drafts with subject lines
- SEO-optimized social media variations
- A headline bank for A/B testing
- A campaign strategy brief

---

### Phase 6: Output Storage

**Step 15 — Save the artifact**
The agent writes the output to disk at:
```
runtime/reviews/{job_id}/output.md
```
A metadata file is also written:
```
runtime/reviews/{job_id}/metadata.json
```
This contains the job ID, owner, timestamp, model used, and token count.

**Step 16 — Update the database**
The `job_records` entry is updated with status `completed`, a timestamp, and a reference to the output file path.

**Step 17 — Log a reflection**
A reflection record is written to the `reflection_records` table. This captures what the agent did, how it approached the task, and what could be improved. Over time, these reflections feed back into the skill records that inform future job handling.

---

### Phase 7: Review and Delivery

**Step 18 — Hermes review (if required)**
If `review_required: true` was set in the task envelope, the completed job is flagged for review. Hermes reads the output, checks it against the original goal, and either approves it or flags issues. If issues are found, the job can be re-queued with revision notes.

**Step 19 — Delivery**
The finished output is available:
- In the file system at `runtime/reviews/{job_id}/`
- Via the BizBrain API using the job ID
- The status is visible in the queue status endpoint

**Step 20 — Iterate**
If the client wants revisions, they submit a new task envelope referencing the original job ID. The system treats it as a fresh job and the cycle repeats — this time with the context of what was already produced.

---

## Status Lifecycle

Every job passes through these statuses in order:

| Status | Meaning |
|--------|---------|
| `pending` | Job received and written to the database |
| `queued` | Job pushed to Redis, waiting for a worker |
| `active` | Worker has dequeued the job and is processing it |
| `in_review` | Output complete, awaiting Hermes quality check |
| `completed` | All done, artifact stored and available |
| `escalated` | Job hit a high-risk trigger and needs human review |
| `failed` | An error occurred; job logged for retry or manual handling |

---

## Marketing Task Types Supported

| task_type | What it does |
|-----------|-------------|
| `content_prep` | Writes original marketing content: emails, posts, copy, scripts |
| `rewrite` | Rewrites or edits existing content to a new tone/audience |
| `classification` | Categorizes and tags content assets |
| `skill_extraction` | Analyzes past work to extract repeatable patterns |
| `implementation` | Builds multi-part deliverables: campaigns, landing pages, funnels |

---

## Example Marketing Jobs

### Job A — Social Media Campaign
```json
{
  "title": "Instagram Campaign Copy — Summer Product Drop",
  "goal": "Write 10 Instagram caption variations for a streetwear summer drop. Tone: hype, Gen Z, short sentences.",
  "task_type": "content_prep",
  "risk_tier": "low",
  "preferred_owner": "hermes"
}
```
**Typical output:** 10 captions with 3-5 hashtag suggestions each, plus a bio link CTA.

---

### Job B — Email Sequence
```json
{
  "title": "5-Part Nurture Sequence — SaaS Trial Users",
  "goal": "Write a 5-email drip sequence to convert free trial users to paid. Audience: startup operators. Tone: friendly but direct.",
  "task_type": "content_prep",
  "risk_tier": "medium",
  "preferred_owner": "hermes"
}
```
**Typical output:** 5 emails with subject lines, preview text, body copy, and CTA buttons for each.

---

### Job C — Landing Page Build
```json
{
  "title": "Full Landing Page — New Product Launch",
  "goal": "Create a complete landing page structure for a new B2B tool. Includes headline, sub-headline, 3 feature sections, social proof, FAQ, and CTA.",
  "task_type": "implementation",
  "risk_tier": "high",
  "preferred_owner": "agent_zero",
  "review_required": true
}
```
**Typical output:** HTML/CSS landing page draft + copy brief + conversion strategy notes.

---

## Infrastructure Summary

| Component | Details |
|-----------|---------|
| Server | VPS at 31.220.49.96, Ubuntu, 24/7 uptime |
| API Gateway | BizBrain Lite — FastAPI, port 18000 |
| Queue | Redis, keys: `flow:{owner}:jobs` |
| Database | PostgreSQL 17, table: `job_records` |
| LLM Gateway | OpenRouter (routes to GPT-4o, Claude, Mistral) |
| Monitoring | Portainer UI at port 9000 |
| Workers | Docker containers: flow-hermes-worker, flow-openclaw-worker, flow-agent-zero-worker |

---

## What FLOW Does Not Do (Yet)

- It does not publish to social media platforms directly
- It does not connect to design tools (Figma, Canva) yet
- It does not send emails directly — it generates the email content
- It does not have a client-facing UI — interaction is via API or direct file access

These are planned integrations. The current system handles content generation, routing, and artifact storage.

---

## Glossary

**Task Envelope** — The structured JSON object that describes a job. Analogous to a creative brief.

**Owner** — The agent assigned to execute the job (hermes, openclaw, or agent_zero).

**Redis Queue** — A fast in-memory message queue. Jobs wait here between validation and execution.

**BRPOP** — A Redis command that blocks a worker until a job appears. Efficient and instant.

**Reflection Record** — A post-job log entry capturing what the agent did and what it learned.

**Skill Record** — A reusable pattern extracted from completed jobs. Used to improve future performance.

**OpenRouter** — An API service that provides access to multiple LLMs (GPT-4o, Claude, Mistral) through one endpoint.

**risk_tier** — A field in the task envelope that tells the router how carefully to handle a job. Low risk runs autonomously. High risk triggers review or escalation.
