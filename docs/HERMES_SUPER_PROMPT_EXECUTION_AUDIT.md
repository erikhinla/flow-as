# 1. Executive status

## Current state snapshot
- **Hermes execution center:** available in `flow-as` and already documented as runtime governor with escalation policy.
- **FLOW Agent AS deployability:** mostly ready at orchestration layer (BizBrain Lite, intake webhook, Docker deployment runbooks, env reference).
- **TransformBy10X repo audit:** **blocked** from this environment due GitHub network restriction (HTTP 403 tunnel failure during clone).
- **BizBuilders surface:** partial assets exist (intake assessment, routing logic, schema) but no complete public web surface or checkout route in this repo.
- **BizBot Mktng surface:** naming exists in docs context, but no production site routes/assets for RevAnew + Reddit Marketing Guide in this repo.
- **Social launch system:** message templates exist; platform-to-offer CTA plumbing is not fully defined as an execution matrix.

## Launch posture
- **Hermes solo launch is feasible** for FLOW Agent AS control-plane operations.
- **Commercial launch across all four properties is not yet ready** because domain authority, payment plumbing, CRM destinations, analytics attribution, and legal page baseline are not fully implemented in code/config.

---

# 2. Repo audit by property

## A) FLOW Agent AS (`flow-as`)

### Structure and execution surfaces
- **Control plane API:** `services/bizbrain_lite/app/` (FastAPI routers, DB models, queue services).
- **Deployment docs:** `DEPLOYMENT.md`, `docs/2026-MBP-DEPLOYMENT.md`, `docs/PRODUCTION_ENV_REFERENCE.md`, `scripts/deploy_minimal_stack.sh`.
- **Intake surface:** `services/bizbrain_lite/app/api/openclaw_intake.py` and `intake-webhook/app.py`.
- **BizBuilders intake content:** `BIZBUILDERS/systems/intake/`.

### Key routes present (flow-as)
- `/v1/health`
- `/v1/capabilities`
- `/v1/flow/health`
- `/v1/flow/workers`
- `/v1/flow/queues/summary`
- `/v1/intake/task`
- `/v1/intake/status`
- `/v1/intake/queues/status`
- `/health` (intake-webhook)
- `/intake` (intake-webhook)
- `/intake/submissions` (intake-webhook, gated by `WEBHOOK_API_KEY`)

### Terminology and canon conflicts (flow-as)
1. **`FLOW Agent OS` vs `FLOW Agent AS` vs `Execution Engine`**
   - Conflict: all three terms used as primary identifiers.
   - Canonical replacement: use **FLOW Agent Architected Schemas (FAAS)** as system name; keep **Execution Engine** as functional descriptor.
2. **`runtime` vs `Execution Engine`**
   - Conflict: multiple docs still use `runtime` framing where governance docs prescribe `Execution Engine`.
   - Canonical replacement: **Execution Engine** for governed orchestration behavior.
3. **BizBot naming drift (`BizBot` vs `BizBot Mktng`)**
   - Conflict: docs reference `BizBot`; launch asks for `BizBot Mktng` where brand naming calls for it.
   - Canonical replacement: **BizBot Mktng** for offer-facing brand surfaces; keep `BizBot` only where historical architecture references require it.
4. **Layer vocabulary drift**
   - Current repo predominantly uses **layers**. Maintain this term consistently.

### Missing launch-critical pages/assets in flow-as
- No production website routes for:
  - TransformBy10X landing + Fog Diagnostic funnel.
  - BizBuilders AI offer + 15-question diagnostic web surface.
  - BizBot Mktng offer stack (RevAnew + Reddit Marketing Guide checkout/delivery).
- No explicit legal-page templates (privacy policy, terms, disclaimers, refund policy).
- No unified social CTA routing map to live destination URLs.

### Deployment blockers (flow-as)
- Root `docker-compose.yml` not present in this checkout while docs/scripts reference it.
- Payment integrations not defined (Stripe/checkout/webhook handlers absent).
- CRM destination not defined (HubSpot/GoHighLevel/Notion/Airtable destination unresolved).
- Attribution plan not implemented (UTM policy + analytics events + conversion IDs incomplete).

### Exact next-step sequence (flow-as)
1. Establish deployment authority doc + branch rules in-repo (single source of truth).
2. Add/restore root `docker-compose.yml` aligned with runbooks.
3. Create env var registry with required/optional + ownership + rotation policy.
4. Implement lead ingress standard (forms → webhook/API → CRM destination).
5. Implement checkout + fulfillment services for paid offers.
6. Add analytics instrumentation plan and event schema.
7. Add legal page baseline and link in all surface footers.

## B) TransformBy10X (`tbtx-next-ecosystem`)

### Audit status
- **Repo inspection blocked in this environment** (clone failure due GitHub network restriction).

### Implication
- Any statement about routes/pages/config in this property is **assumption-only** until repo is inspectable.

### Immediate remediation artifact required
- Add offline audit checklist ticket in FLOW Agent AS queue:
  - clone repo in deploy environment with network access
  - inventory routes/offers/forms/env vars
  - map Fog Diagnostic → Fog Lift Kit → BizBuilders progression

## C) BizBuilders AI (business surface)

### Existing assets in flow-as
- Context Architecture Assessment markdown + JSON schema.
- Intake routing logic with sequence enforcement.
- Intake webhook service with submission persistence.

### Missing for production surface
- Public web app routes/pages and submission UI.
- 15-question B2B diagnostic implementation with scoring/routing automation.
- CRM sync + email sequence integration.
- Acceptance criteria and QA checklist for public deployment.

## D) BizBot Mktng (business surface)

### Existing assets in flow-as
- Only indirect references in docs and archived materials.

### Missing for production surface
- Dedicated web routes/pages.
- RevAnew offer definition in site copy and checkout.
- Reddit Marketing Guide product page, checkout, and digital delivery automation.
- Post-purchase email + access flow.

---

# 3. Canon / terminology alignment map

| Canonical term (approved) | Rejected alternatives | Where it must appear | Rename/update surfaces |
|---|---|---|---|
| FLOW = **Frictionless Leveraged Orchestrated Workflows** | FLOW as undefined acronym | Brand docs, repo overview, external copy | `docs/*` positioning and marketing docs |
| **FLOW Agent Architected Schemas (FAAS)** | FLOW Agent OS / FLOW Agent AS as primary headline | System naming across README/docs/deploy pages | Deployment, positioning, prompts, press kit |
| **Execution Engine** (functional role) | runtime (as primary system label) | Architecture docs and control-plane descriptions | Any doc where runtime is used as the core brand term |
| **quad-kernel keystone** = folders, markdowns, scripts, protocols | ad hoc “framework pieces” phrasing | Operating model and implementation guidance | New launch docs + internal runbooks |
| **intelligence isn’t in the tools, it’s in the infrastructure** | tool-first capability claims | Offer pages, social proof sections | TransformBy10X + BizBuilders proof blocks |
| **INFRA4ALL** | inconsistent hashtag/phrase variants | Social assets + manifesto sections | Platform templates and campaign copy |
| **layers** | plates (in this repo context) | Diagnostics, routing logic, architecture maps | Keep current layer language; avoid introducing plates |
| **BizBot Mktng** | BizBot Marketing / BizBot (offer-facing) | Offer pages, CTA copy, social assets | BizBot public surfaces and checkout copy |

---

# 4. Domain / product / repo map

| Domain / property | Repo | Brand | Audience | Diagnostic | Core offer | Primary CTA | Next step after conversion |
|---|---|---|---|---|---|---|---|
| `flow-agent` orchestration surface (domain TBD) | `flow-as` | FLOW / FAAS | Operator, builder, internal execution team | FLOW task intake envelope | Governed execution + routing | Submit bounded task | Review queue + execute via owner-assigned agent |
| `transformby10x.ai` | `tbtx-next-ecosystem` (not inspectable here) | TransformBy10X | B2C founder/operator with digital fog | Fog Diagnostic | Fog Lift Kit ($7.77) | Take Fog Diagnostic | Offer progression to BizBuilders AI diagnostic |
| `bizbuilders.ai` (target) | likely `tbtx-next-ecosystem` or dedicated repo (TBD) | BizBuilders AI | B2B operators needing infrastructure | 15-question B2B diagnostic + context assessment | Infrastructure engagement | Submit diagnostic | Route to scoped conversation / implementation intake |
| `bizbotmktng` surface/domain TBD | repo TBD | BizBot Mktng | Growth-stage operators needing activation | Activation readiness checkpoint | RevAnew + Reddit Marketing Guide ($97 lifetime) | Get guide / start RevAnew | Delivery bundle + CRM-tagged nurture sequence |

---

# 5. Launch architecture by brand

## FLOW / FAAS
- **Purpose:** governed execution backbone.
- **Target audience:** operator and implementation team.
- **Main offer:** execution infrastructure and agent routing.
- **Supporting proof:** queue governance, review gates, durable state, flow health endpoints.
- **Primary CTA:** submit bounded task envelope.
- **Secondary CTA:** run health checks + review status.
- **Funnel destination:** queue assignment (`openclaw`, `hermes`, `agent_zero`).
- **Dependencies:** Postgres, Redis, API token, compose stack.
- **Done means:** stack up + intake accepted + queue depth updates + review path operational.

## TransformBy10X
- **Purpose:** B2C entry and doctrine surface.
- **Target audience:** founders/operators in execution fog.
- **Main offer:** Fog Diagnostic → Fog Lift Kit.
- **Supporting proof:** Production Hub, Showrunner Suite, Prompting Circumstance.
- **Primary CTA:** start Fog Diagnostic.
- **Secondary CTA:** purchase Fog Lift Kit.
- **Funnel destination:** BizBuilders AI progression.
- **Dependencies:** landing routes, payment, email, analytics, CRM handoff.
- **Done means:** diagnostic flow + paid conversion + tracked progression event.

## BizBuilders AI
- **Purpose:** infrastructure offer surface.
- **Target audience:** B2B orgs needing workflow architecture.
- **Main offer:** 15-question B2B diagnostic + infrastructure engagement.
- **Supporting proof:** assessment artifacts, routing logic, canonical sequencing.
- **Primary CTA:** submit B2B diagnostic.
- **Secondary CTA:** book infrastructure conversation.
- **Funnel destination:** scoped implementation intake.
- **Dependencies:** web routes, webhook/API capture, CRM tagging, qualification rubric.
- **Done means:** diagnostic submitted, routed, CRM record created, follow-up triggered.

## BizBot Mktng
- **Purpose:** activation and growth execution surface.
- **Target audience:** operators needing channel execution.
- **Main offer:** RevAnew + Reddit Marketing Guide.
- **Supporting proof:** deliverable components (Account Intelligence Report, Karma Kickstarter, Marketing Roadmap).
- **Primary CTA:** buy Reddit Marketing Guide ($97 lifetime).
- **Secondary CTA:** start RevAnew.
- **Funnel destination:** delivery workflow + nurture path.
- **Dependencies:** checkout, fulfillment asset hosting, email/CRM automation.
- **Done means:** successful purchase, instant delivery, attribution captured, lifecycle tag applied.

---

# 6. Offer structure

| Offer | Audience | Problem | Deliverable | Price | CTA | Where it lives | After signup/purchase | Proof |
|---|---|---|---|---|---|---|---|---|
| Fog Diagnostic | B2C operators | Lack of clarity on execution friction | Diagnostic result + fog-level path | Free (assumed) | Start diagnostic | TransformBy10X | Route to Fog Lift Kit + BizBuilders progression | Proof-of-system modules and case artifacts |
| Fog Lift Kit | Same as above | Need immediate action rhythm | 20-minute daily practice tailored to industry + Fog Level | **$7.77** | Get Fog Lift Kit | TransformBy10X checkout | Delivery email + daily practice onboarding | Completion + before/after execution baseline |
| BizBuilders AI 15-question B2B diagnostic | B2B teams | Infrastructure gaps and workflow breakdowns | Structured gap profile + routing result | Free lead diagnostic | Submit diagnostic | BizBuilders AI | CRM record + qualification + infrastructure call path | Existing context assessment/routing framework |
| RevAnew | Growth-stage operators | Inconsistent activation engine | Activation package (exact scope to define in product spec) | TBD | Start RevAnew | BizBot Mktng | Onboarding workflow + implementation path | Operational KPI uplift proof |
| Reddit Marketing Guide | Founder/operator marketers | Low-signal Reddit execution | Account Intelligence Report + Karma Kickstarter + Marketing Roadmap | **$97 lifetime** | Buy guide | BizBot Mktng | Instant digital delivery + CRM lifecycle tagging | Guide outcomes/case snippets |

---

# 7. Missing but required

## Explicit audit of required items
- [x] Domain-to-repo map — **defined but partially provisional** due inaccessible repos.
- [x] Production authority — **defined** (GitHub source-control authority; Docker+Hostinger deployment authority).
- [x] Branch/deployment rules — **defined** (feature branch first, no direct main mutation, review before merge).
- [~] Env vars — **partially defined** for flow-as; missing complete cross-property inventory.
- [ ] Analytics/attribution — **missing** unified event taxonomy and platform implementation map.
- [ ] Payment flow — **missing** concrete provider, checkout routes, webhook handlers.
- [ ] Delivery flow — **missing** post-purchase automation spec.
- [ ] Email/CRM destination — **missing** canonical destination and field mapping.
- [~] Proof-of-system placement — **partially defined** in copy goals, not fully mapped to routes.
- [ ] Legal pages — **missing** enforceable baseline routes/content.
- [ ] Asset dependencies — **missing** source-of-truth directory and ownership matrix.
- [x] Launch order — **defined** in execution sequence below.
- [ ] Acceptance criteria per site — **missing in codebase for TransformBy10X/BizBuilders/BizBot surfaces**.

## Env var inventory (current flow-as extraction)

### Required (stack/deploy docs + scripts)
- `A0_AUTH_LOGIN`
- `A0_AUTH_PASSWORD`
- `BIZBRAIN_ENV`
- `BIZBRAIN_API_TOKEN`
- `FLOW_DB_PASSWORD`
- `OPENAI_API_KEY`
- `POSTIZ_DOMAIN`
- `POSTIZ_JWT_SECRET`
- `POSTIZ_DB_PASSWORD`
- `HERMES_DEFAULT_MODEL`

### Required by runtime codepaths
- `BIZBRAIN_REDIS_URL` (or `REDIS_URL` fallback)
- `SOCIAL_HUB_API_ORIGIN`
- `WEBHOOK_API_KEY` (for intake submissions listing auth)

### Optional / secondary
- `GOOGLE_API_KEY`
- `GROQ_API_KEY`
- `MERCURY2_GATEWAY_TOKEN`
- `MERCURY2_IMAGE`
- `GITHUB_TOKEN`
- `DISCORD_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `FIRECRAWL_API_KEY`
- `POSTIZ_DISABLE_REGISTRATION`

## Asset/source-of-truth location baseline
- **Source-of-truth docs:** `docs/` (authority and runtime rules).
- **Operational prompts:** `prompts/`.
- **Intake/offer draft assets:** `BIZBUILDERS/systems/intake/`.
- **Runtime state examples:** `runtime/`, `memory/`.
- **Missing:** centralized `launch-assets/` folder with platform variants + canonical CTA map.

## Minimum operator input packet to proceed (besides API keys)

> Do **not** paste raw secrets into chat. Provide placeholders here and load real values into `.env` or secret manager.

## Secret handling protocol (operator-safe)

- **Do not post API keys in chat.**
- Use one of these approved paths:
  1. Add secrets directly to host/runtime `.env` files.
  2. Store secrets in a secret manager and inject at deploy time.
  3. Share only masked values in chat (`sk-****...`) for verification.
- Rotation rule: if any key was previously exposed in chat, rotate before production use.
- Agent workflow rule: agents can update config/schema/docs and wiring, but should not require raw key values in chat to proceed.

### 1) Authority and deployment decisions (required)
- Production Git branch: confirm (`main` or other protected branch).
- Merge gate: PR approvals required (yes/no, count).
- Deployment authority per property:
  - FLOW/FAAS runtime host (Hostinger/VPS path).
  - TransformBy10X runtime host.
  - BizBuilders runtime host.
  - BizBot Mktng runtime host.

### 2) Domain and DNS map (required)
- Final production domains/subdomains for:
  - FLOW/FAAS control plane
  - transformby10x.ai
  - bizbuilders.ai
  - BizBot Mktng surface
- DNS provider + who can create records.

### 3) Payments and fulfillment (required for paid offers)
- Checkout provider account to use (Stripe/Gumroad/other).
- Product IDs/prices to set:
  - Fog Lift Kit = **$7.77**
  - Reddit Marketing Guide = **$97 lifetime**
- Fulfillment destination:
  - Immediate download URL(s) and/or email template IDs.

### 4) Lead capture and CRM destination (required)
- Canonical CRM destination (HubSpot/GoHighLevel/Airtable/Notion/etc.).
- Required contact fields + pipeline stage mapping.
- Owner assignment rule for new leads (who receives what).

### 5) Analytics and attribution (required)
- Analytics stack decision (GA4/PostHog/other).
- Attribution convention: UTM schema (`source`, `medium`, `campaign`, `content`).
- Conversion events to track:
  - Diagnostic started
  - Diagnostic submitted
  - Purchase completed
  - Progression to next property

### 6) Legal baseline (required for public launch)
- Canonical legal entity name and address block.
- Policy URLs or approved policy text for:
  - Privacy Policy
  - Terms
  - Refund Policy
  - Disclaimer

### 7) Asset source-of-truth (required)
- Single folder/repo to store final launch assets.
- Brand-approved logo pack + color/type tokens.
- Final CTA URL registry (one URL per offer CTA).

---

# 8. Ordered execution sequence

1. **Objective:** lock authority and branch/deploy rules for all properties.  
   **Artifact:** `LAUNCH_AUTHORITY.md` with production authority + branch policy + deploy ownership.  
   **Dependency:** none.  
   **Done condition:** one unambiguous authority doc linked by all repos.

2. **Objective:** produce canonical domain-to-repo map and ownership matrix.  
   **Artifact:** `DOMAIN_REPO_OPERATIONS_MAP.md`.  
   **Dependency:** step 1.  
   **Done condition:** each domain has one repo authority, one deploy target, one owner.

3. **Objective:** complete repository audits for inaccessible properties.  
   **Artifact:** `REPO_AUDIT_tbtx-next-ecosystem.md` and any additional repo audits.  
   **Dependency:** step 2 and network access.  
   **Done condition:** routes/config/env/copy conflicts inventoried per repo.

4. **Objective:** enforce canon terminology across docs and UI copy.  
   **Artifact:** `TERMINOLOGY_ALIGNMENT_PATCHSET.md` + file-by-file rename list.  
   **Dependency:** step 3.  
   **Done condition:** zero unresolved naming conflicts in active launch surfaces.

5. **Objective:** define and implement lead capture + CRM destination.  
   **Artifact:** form schema, webhook handlers, CRM field map, test payloads.  
   **Dependency:** step 3.  
   **Done condition:** every CTA writes a traceable lead/contact record.

6. **Objective:** implement payment + delivery plumbing for paid offers.  
   **Artifact:** checkout routes, payment webhook handlers, fulfillment workflow spec.  
   **Dependency:** step 5.  
   **Done condition:** paid purchase triggers immediate delivery and CRM tagging.

7. **Objective:** implement analytics + attribution plan.  
   **Artifact:** event taxonomy, UTM conventions, conversion dashboard mapping.  
   **Dependency:** step 5 and step 6.  
   **Done condition:** diagnostic starts, purchases, and handoffs are attributable by source.

8. **Objective:** finalize legal baseline.  
   **Artifact:** privacy, terms, refund, disclaimer pages and shared footer links.  
   **Dependency:** step 6.  
   **Done condition:** all public pages link legal routes and policy text is published.

9. **Objective:** launch TransformBy10X B2C funnel.  
   **Artifact:** live routes for Fog Diagnostic + Fog Lift Kit.  
   **Dependency:** steps 4-8.  
   **Done condition:** end-to-end diagnostic-to-purchase path works and is tracked.

10. **Objective:** launch BizBuilders AI diagnostic surface.  
    **Artifact:** 15-question B2B diagnostic route + routing automation.  
    **Dependency:** steps 4-8 and TransformBy10X progression hooks.  
    **Done condition:** qualified leads route into infrastructure conversation queue.

11. **Objective:** launch BizBot Mktng paid assets.  
    **Artifact:** RevAnew and Reddit Marketing Guide product + checkout + delivery pages.  
    **Dependency:** steps 6-8.  
    **Done condition:** $97 offer purchase/delivery + attribution verified.

12. **Objective:** launch social asset operating loop.  
    **Artifact:** platform asset packs + CTA routing sheet + posting runbook.  
    **Dependency:** steps 9-11.  
    **Done condition:** every post variant maps to a live destination with measurable conversion events.

---

# 9. What done means for each property

## FLOW / FAAS done criteria
- Control plane APIs healthy (`/v1/health`, `/v1/flow/health`, `/v1/intake/status`).
- Task intake creates queueable jobs and route ownership is correct.
- Review gate path exists for high-risk tasks.
- Deployment and rollback runbooks tested on target host.

## TransformBy10X done criteria
- Live homepage, Fog Diagnostic flow, and Fog Lift Kit checkout.
- Price locked at $7.77 in UI and backend product config.
- Daily practice fulfillment personalized by industry + Fog Level.
- Progression event to BizBuilders AI is automated and tracked.

## BizBuilders AI done criteria
- 15-question diagnostic route live and validated.
- Responses persisted, scored/routed, and pushed to CRM.
- Follow-up workflow delivers next-step artifact within defined SLA.
- Messaging aligns with infrastructure/context/leverage/workflows/execution vocabulary.

## BizBot Mktng done criteria
- Brand spelling `Mktng` enforced across all public surfaces.
- RevAnew offer route live with defined conversion action.
- Reddit Marketing Guide route live at $97 lifetime.
- Delivery package includes: Account Intelligence Report, Karma Kickstarter, Marketing Roadmap.

---

# 10. Social media asset system

## Platform operating map

| Platform | Content role | CTA role | Offer destination | Recommended post types | Launch sequence role | Asset variants needed |
|---|---|---|---|---|---|---|
| LinkedIn | Authority + operator narrative | Diagnostic and infrastructure CTA | TransformBy10X + BizBuilders AI | Founder posts, carousel explainers, case breakdowns | Early trust + mid-funnel conversion | Text post, carousel, quote card, long-form article |
| Skool | Community activation + retention | Participation to diagnostic/offer CTA | BizBuilders AI + RevAnew | Workshop prompts, checklists, office-hours recaps | Nurture and community conversion | Prompt cards, worksheet PDFs, session recap templates |
| Instagram/Facebook | Awareness + quick conversion | Link-in-bio to low-friction entry offers | Fog Diagnostic + Fog Lift Kit | Reels, short carousels, story polls, testimonial clips | Top-of-funnel volume | Reel scripts, cover tiles, story sticker templates |
| YouTube | Deep proof-of-system education | Description CTA to diagnostics/offers | TransformBy10X + BizBuilders + BizBot Mktng | Explainers, teardown videos, walkthroughs | Mid/low funnel authority conversion | Thumbnail set, chaptered script, end-screen CTA cards |
| X.com | Real-time distribution + hooks | Thread CTA to single funnel endpoint | Fog Diagnostic primary; Reddit Guide secondary | Threads, proof snapshots, launch updates | Fast iteration and traffic testing | Hook bank, thread templates, quote images |

## Content buckets
1. **Digital fog diagnostics** (problem identification).
2. **Infrastructure proof** (Execution Engine + governance + outputs).
3. **Offer walk-throughs** (what user gets, price, next step).
4. **Operator implementation logs** (before/after operational clarity).
5. **Case artifacts** (screenshots, route maps, checklists).

## Platform-to-offer map
- LinkedIn → BizBuilders AI diagnostic.
- Skool → RevAnew + BizBuilders implementation discussions.
- Instagram/Facebook → Fog Diagnostic / Fog Lift Kit.
- YouTube → TransformBy10X doctrine + BizBuilders progression.
- X.com → Fog Diagnostic (primary), Reddit Marketing Guide (campaign pushes).

## Post-to-CTA map
- Problem-framing post → `Start Fog Diagnostic`.
- System-proof post → `See how infrastructure route works` (to BizBuilders diagnostic).
- Offer post (low-ticket) → `Get Fog Lift Kit ($7.77)`.
- Offer post (activation) → `Get Reddit Marketing Guide ($97 lifetime)`.
- Community post → `Join implementation thread / submit B2B diagnostic`.

## Asset production checklist
- [ ] Canon headline bank (FLOW/FAAS/INFRA4ALL terms only).
- [ ] CTA URL registry (one source of truth per offer).
- [ ] UTM matrix by platform/campaign/post type.
- [ ] Copy variants by platform (short, medium, long).
- [ ] Visual template set (1:1, 4:5, 9:16, 16:9).
- [ ] Proof-of-system artifact library (screens, snippets, outcomes).
- [ ] Approval + publish workflow and owner assignment.
- [ ] Post-publish tracking workflow (click, lead, purchase, progression).
