import datetime
import json
import os
import pathlib
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

INTAKE_DIR = pathlib.Path("/data/intake")
INTAKE_DIR.mkdir(parents=True, exist_ok=True)


class Sub(BaseModel):
    name: str
    email: str
    company: Optional[str] = ""
    answers: dict = {}
    friction: str = ""
    stalling: str = ""
    gaps: Optional[dict] = {}
    routing: Optional[str] = ""
    source: Optional[str] = "bizbuilders.ai/intake"
    submitted_at: Optional[str] = ""


class DiagnosticAnswer(BaseModel):
    question_id: str
    answer_value: int
    answer_label: str = ""
    dimension: str = ""


class DiagnosticSub(BaseModel):
    name: str
    email: str
    company: Optional[str] = ""
    role: Optional[str] = ""
    industry: Optional[str] = ""
    diagnostic_type: str = "tbtx"
    source: Optional[str] = "transformby10x.ai/diagnostic"
    utm_source: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    answers: List[DiagnosticAnswer]


DIAGNOSTICS: Dict[str, dict] = {
    "tbtx": {
        "brand": "TransformBy10X",
        "title": "Digital Fog Diagnostic",
        "audience": "B2C founders, creators, operators, and professionals",
        "path": "/diagnostic?type=tbtx",
        "source": "transformby10x.ai/diagnostic",
        "cta": "Get Your Custom Roadmap",
        "route_to": "bizbuilders.ai/roadmap",
        "intro": "Find where your personal execution system is leaking attention, momentum, and AI leverage.",
        "questions": [
            {
                "id": "tbtx_q1",
                "dimension": "clarity",
                "label": "How clear is the outcome you are trying to build over the next 30 days?",
                "low": "Very clear",
                "high": "Mostly foggy",
            },
            {
                "id": "tbtx_q2",
                "dimension": "attention",
                "label": "How often do you switch tools, tabs, notes, or ideas before finishing the thing you started?",
                "low": "Rarely",
                "high": "Constantly",
            },
            {
                "id": "tbtx_q3",
                "dimension": "folders",
                "label": "How easy is it to find the files, links, prompts, assets, and decisions for one active project?",
                "low": "Easy",
                "high": "Hard",
            },
            {
                "id": "tbtx_q4",
                "dimension": "markdowns",
                "label": "How much of your thinking exists in reusable briefs, checklists, docs, or templates?",
                "low": "Most of it",
                "high": "Almost none",
            },
            {
                "id": "tbtx_q5",
                "dimension": "scripts",
                "label": "How many repeated tasks still require you to manually remember each step?",
                "low": "Very few",
                "high": "Most of them",
            },
            {
                "id": "tbtx_q6",
                "dimension": "protocols",
                "label": "When work gets messy, do you have a rule for what to do next?",
                "low": "Yes",
                "high": "No",
            },
            {
                "id": "tbtx_q7",
                "dimension": "ai_readiness",
                "label": "How ready is your current setup for AI or agents to produce useful work without heavy babysitting?",
                "low": "Ready",
                "high": "Not ready",
            },
            {
                "id": "tbtx_q8",
                "dimension": "handoff",
                "label": "Could someone else understand your current workflow from the artifacts you already have?",
                "low": "Yes",
                "high": "No",
            },
            {
                "id": "tbtx_q9",
                "dimension": "offer",
                "label": "How clearly can you explain the transformation you help people achieve?",
                "low": "Clearly",
                "high": "Not clearly",
            },
            {
                "id": "tbtx_q10",
                "dimension": "capture",
                "label": "When someone is interested in your work, how reliable is the path from interest to next action?",
                "low": "Reliable",
                "high": "Leaky",
            },
            {
                "id": "tbtx_q11",
                "dimension": "momentum",
                "label": "How often do good ideas stall because the structure to execute them is not already there?",
                "low": "Rarely",
                "high": "Often",
            },
            {
                "id": "tbtx_q12",
                "dimension": "measurement",
                "label": "How clearly can you tell what is working, what is stalled, and what should be changed?",
                "low": "Clearly",
                "high": "Unclear",
            },
        ],
    },
    "bizbuilders": {
        "brand": "BizBuilders AI",
        "title": "Infrastructure Readiness Diagnostic",
        "audience": "B2B operators, agencies, consultants, and growth teams",
        "path": "/diagnostic?type=bizbuilders",
        "source": "bizbuilders.ai/roadmap",
        "cta": "Activate Growth System",
        "route_to": "bizbotmktng/activation",
        "intro": "Map the business infrastructure gaps blocking repeatable lead capture, delivery, automation, and growth.",
        "questions": [
            {
                "id": "bbai_q1",
                "dimension": "offer",
                "label": "How clearly is your core offer packaged, named, scoped, and tied to a measurable business outcome?",
                "low": "Very clearly",
                "high": "Unclear",
            },
            {
                "id": "bbai_q2",
                "dimension": "audience",
                "label": "How specific is your target buyer, use case, urgency, and trigger event?",
                "low": "Specific",
                "high": "Too broad",
            },
            {
                "id": "bbai_q3",
                "dimension": "capture",
                "label": "How reliable is your lead capture path from traffic source to stored contact record?",
                "low": "Reliable",
                "high": "Leaky",
            },
            {
                "id": "bbai_q4",
                "dimension": "qualification",
                "label": "How consistently do you qualify leads before sales or fulfillment time is spent?",
                "low": "Consistently",
                "high": "Inconsistently",
            },
            {
                "id": "bbai_q5",
                "dimension": "crm",
                "label": "How cleanly do new leads enter a CRM, pipeline, owner assignment, and follow-up sequence?",
                "low": "Cleanly",
                "high": "Messy",
            },
            {
                "id": "bbai_q6",
                "dimension": "folders",
                "label": "How organized are campaign assets, SOPs, client files, sales docs, and delivery materials?",
                "low": "Organized",
                "high": "Scattered",
            },
            {
                "id": "bbai_q7",
                "dimension": "markdowns",
                "label": "How much of your sales, delivery, and operations knowledge is documented in reusable templates?",
                "low": "Most of it",
                "high": "Almost none",
            },
            {
                "id": "bbai_q8",
                "dimension": "scripts",
                "label": "How many repeated operational tasks still depend on manual copy/paste, memory, or one person's habits?",
                "low": "Few",
                "high": "Many",
            },
            {
                "id": "bbai_q9",
                "dimension": "protocols",
                "label": "How explicit are your rules for lead routing, escalation, approval, delivery QA, and handoff?",
                "low": "Explicit",
                "high": "Implicit",
            },
            {
                "id": "bbai_q10",
                "dimension": "delivery",
                "label": "How repeatable is your client/customer delivery process from kickoff to outcome?",
                "low": "Repeatable",
                "high": "Reinvented each time",
            },
            {
                "id": "bbai_q11",
                "dimension": "analytics",
                "label": "How clearly can you connect source, campaign, diagnostic, purchase, and follow-up behavior?",
                "low": "Clearly",
                "high": "Cannot connect",
            },
            {
                "id": "bbai_q12",
                "dimension": "automation",
                "label": "How well do your automations support the workflow instead of creating more exceptions?",
                "low": "They support it",
                "high": "They create exceptions",
            },
            {
                "id": "bbai_q13",
                "dimension": "ai_readiness",
                "label": "How safely could an AI agent draft, route, or execute work using your existing context?",
                "low": "Safely",
                "high": "Not safely",
            },
            {
                "id": "bbai_q14",
                "dimension": "governance",
                "label": "How clear are the approval rules for money, customer promises, production changes, or brand-sensitive work?",
                "low": "Clear",
                "high": "Unclear",
            },
            {
                "id": "bbai_q15",
                "dimension": "handoff",
                "label": "How easily can work move from marketing to sales to delivery without losing context?",
                "low": "Easily",
                "high": "Context gets lost",
            },
            {
                "id": "bbai_q16",
                "dimension": "scale",
                "label": "If demand doubled this month, how much would break in your current operating system?",
                "low": "Very little",
                "high": "A lot",
            },
        ],
    },
}

DIMENSION_LABELS = {
    "ai_readiness": "AI readiness",
    "analytics": "Analytics and attribution",
    "attention": "Attention and focus",
    "audience": "Audience clarity",
    "automation": "Automation fit",
    "capture": "Lead capture",
    "clarity": "Clarity",
    "crm": "CRM and follow-up",
    "delivery": "Delivery system",
    "folders": "Folders and source of truth",
    "governance": "Governance",
    "handoff": "Handoff",
    "markdowns": "Markdowns and reusable knowledge",
    "measurement": "Measurement",
    "momentum": "Momentum",
    "offer": "Offer clarity",
    "protocols": "Protocols",
    "qualification": "Qualification",
    "scale": "Scale readiness",
    "scripts": "Scripts and repeatable steps",
}

INDUSTRY_CONTEXT = {
    "creator": "For creators, fog usually shows up as scattered content ideas, inconsistent publishing, unclear offers, and no reliable bridge from attention to revenue.",
    "consulting": "For consulting and services, the highest leverage gap is usually the path from diagnostic insight to scoped engagement and repeatable delivery.",
    "agency": "For agencies, the risk is usually handoff loss: marketing promises, sales context, fulfillment tasks, and reporting live in different places.",
    "ecommerce": "For ecommerce, the leverage is in connecting campaign source, offer, purchase behavior, lifecycle follow-up, and product feedback.",
    "health": "For health, wellness, and aesthetics, the system must protect trust: compliant intake, clear expectations, careful follow-up, and controlled claims.",
    "local": "For local businesses, the priority is simple: turn searches, referrals, messages, and calls into one follow-up system that does not leak.",
    "saas": "For SaaS, the infrastructure gap usually lives between acquisition, onboarding, activation, support signals, and expansion motion.",
}


def get_config(diagnostic_type: str) -> dict:
    return DIAGNOSTICS.get(diagnostic_type, DIAGNOSTICS["tbtx"])


def category_for(score: int, max_score: int) -> str:
    ratio = score / max_score if max_score else 0
    if ratio <= 0.35:
        return "Clear"
    if ratio <= 0.55:
        return "Fragmented"
    if ratio <= 0.75:
        return "Stalled"
    return "Critical Fog"


def score_dimensions(answers: List[DiagnosticAnswer]) -> Dict[str, dict]:
    grouped: Dict[str, List[int]] = {}
    for answer in answers:
        if not answer.dimension:
            continue
        grouped.setdefault(answer.dimension, []).append(answer.answer_value)

    scores = {}
    for dimension, values in grouped.items():
        total = sum(values)
        max_total = len(values) * 5
        scores[dimension] = {
            "label": DIMENSION_LABELS.get(dimension, dimension.replace("_", " ").title()),
            "score": total,
            "max_score": max_total,
            "severity": round(total / max_total, 2) if max_total else 0,
        }
    return scores


def industry_context(industry: str) -> str:
    key = (industry or "").strip().lower()
    for token, context in INDUSTRY_CONTEXT.items():
        if token in key:
            return context
    if industry:
        return (
            f"For {industry}, the diagnostic should be read as an infrastructure map: "
            "where attention, capture, documentation, handoff, and follow-up are not yet supporting the outcome."
        )
    return "No industry was provided, so this diagnosis focuses on the general execution system instead of a niche-specific workflow."


def build_report(sub: DiagnosticSub, category: str, dimension_scores: Dict[str, dict]) -> dict:
    ordered = sorted(dimension_scores.items(), key=lambda item: item[1]["severity"], reverse=True)
    top_gaps = ordered[:4]
    gap_labels = [details["label"] for _, details in top_gaps]
    primary_gap = gap_labels[0] if gap_labels else "Execution infrastructure"

    if sub.diagnostic_type == "bizbuilders":
        summary = (
            f"{sub.company or sub.name} is showing a {category.lower()} infrastructure pattern. "
            f"The strongest constraint is {primary_gap.lower()}, which means growth work will keep leaking value until capture, routing, documentation, and delivery rules become one operating system."
        )
        roadmap = [
            "Lock the offer, buyer trigger, and qualification criteria.",
            "Connect lead capture to CRM fields, owner assignment, and follow-up stages.",
            "Create the quad-keystone layer: folders, markdowns, scripts, and protocols.",
            "Add analytics events for diagnostic started, submitted, routed, and converted.",
            "Only then add heavier automation or agent execution."
        ]
        next_move = f"Build the BizBuilders AI Custom Roadmap around {primary_gap.lower()} first."
    else:
        summary = (
            f"{sub.name} is showing a {category.lower()} digital fog pattern. "
            f"The biggest drag is {primary_gap.lower()}, so the next win is not another tool. It is a cleaner personal execution system that can hold decisions, assets, prompts, and next actions."
        )
        roadmap = [
            "Name one active outcome and remove unrelated work from the workspace.",
            "Create one source-of-truth folder for assets, notes, prompts, and decisions.",
            "Turn repeated thinking into markdown checklists or briefs.",
            "Write the next-action protocol for when work stalls.",
            "Route the result into a BizBuilders AI Custom Roadmap when the offer/workflow is ready."
        ]
        next_move = f"Start with {primary_gap.lower()} and build the smallest repeatable workflow around it."

    return {
        "headline": f"{category}: {primary_gap} is the first constraint",
        "summary": summary,
        "industry_context": industry_context(sub.industry or ""),
        "top_gaps": [
            {
                "dimension": dimension,
                "label": details["label"],
                "severity": details["severity"],
                "score": details["score"],
                "max_score": details["max_score"],
            }
            for dimension, details in top_gaps
        ],
        "recommended_infrastructure": [
            "Folders: one source of truth for assets, decisions, and active work.",
            "Markdowns: reusable briefs, checklists, offers, SOPs, and handoff notes.",
            "Scripts: repeatable steps for capture, routing, follow-up, and reporting.",
            "Protocols: rules for escalation, approval, completion, and next action."
        ],
        "phased_plan": roadmap,
        "highest_leverage_next_move": next_move,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "flow-intake-webhook"}


@app.get("/", response_class=HTMLResponse)
def root():
    return index_page()


@app.get("/diagnostic", response_class=HTMLResponse)
def diagnostic_page(type: str = "tbtx"):
    config = get_config(type)
    question_markup = "\n".join(
        f"""
        <fieldset class="question" data-question-id="{q['id']}" data-dimension="{q['dimension']}">
          <legend>{q['label']}</legend>
          <div class="scale-labels"><span>{q['low']}</span><span>{q['high']}</span></div>
          <input aria-label="{q['label']}" type="range" min="1" max="5" value="3" />
        </fieldset>
        """
        for q in config["questions"]
    )
    return render_page(config, question_markup)


@app.get("/tbtx", response_class=HTMLResponse)
def tbtx_page():
    return diagnostic_page("tbtx")


@app.get("/bizbuilders", response_class=HTMLResponse)
def bizbuilders_page():
    return diagnostic_page("bizbuilders")


def index_page() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FLOW Diagnostics</title>
  <style>
    body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f6f1; color: #172033; }
    main { width: min(880px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0; }
    h1 { font-size: clamp(2.2rem, 7vw, 5rem); line-height: 1; margin: 0 0 16px; letter-spacing: 0; }
    p { color: #596271; max-width: 680px; }
    .routes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 28px; }
    a { display: grid; gap: 8px; padding: 20px; border: 3px solid #050505; color: inherit; text-decoration: none; background: white; }
    strong { font-size: 1.15rem; }
    span { color: #596271; }
    @media (max-width: 720px) { .routes { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>FLOW Diagnostics</h1>
    <p>Choose the right diagnostic surface. TransformBy10X is the B2C Digital Fog entry layer. BizBuilders AI is the B2B infrastructure and roadmap layer.</p>
    <div class="routes">
      <a href="/diagnostic?type=tbtx"><strong>TransformBy10X</strong><span>B2C Digital Fog Diagnostic</span></a>
      <a href="/diagnostic?type=bizbuilders"><strong>BizBuilders AI</strong><span>B2B Infrastructure Readiness Diagnostic</span></a>
    </div>
  </main>
</body>
</html>
"""


def render_page(config: dict, question_markup: str) -> str:
    diagnostic_type = "bizbuilders" if config["brand"] == "BizBuilders AI" else "tbtx"
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{config['title']}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg-color: #F4F4F0;
      --text-primary: #050505;
      --accent-red: #E61919;
      --surface-color: #EAE8E3;
      --grid-line: #050505;
      --muted: #4a4a44;
    }}
    * {{ box-sizing: border-box; border-radius: 0 !important; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg-color);
      color: var(--text-primary);
      line-height: 1.5;
      background-image: linear-gradient(to right, rgba(0,0,0,0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.08) 1px, transparent 1px);
      background-size: 50px 50px;
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    nav {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 12px 0 28px;
      color: var(--muted);
      font-size: 0.92rem;
      font-family: "JetBrains Mono", monospace;
      text-transform: uppercase;
      font-weight: 800;
    }}
    nav a {{ color: var(--text-primary); text-decoration: none; font-weight: 900; }}
    nav a:hover {{ color: var(--accent-red); text-decoration: underline; text-underline-offset: 4px; }}
    header {{
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 24px;
      align-items: end;
      margin-bottom: 22px;
      border: 4px solid var(--text-primary);
      background: var(--bg-color);
      padding: 24px;
    }}
    h1 {{
      margin: 0;
      font-family: "Archivo Black", Impact, sans-serif;
      text-transform: uppercase;
      font-size: clamp(2.25rem, 6vw, 5.4rem);
      line-height: 0.86;
      letter-spacing: -0.05em;
    }}
    .eyebrow {{
      color: var(--accent-red);
      font-weight: 900;
      text-transform: uppercase;
      font-size: 0.82rem;
      margin-bottom: 10px;
      font-family: "JetBrains Mono", monospace;
      letter-spacing: 0.08em;
    }}
    p {{ margin: 0; color: var(--muted); }}
    .brief {{
      display: grid;
      gap: 12px;
      padding-bottom: 8px;
    }}
    form, .result {{
      background: var(--bg-color);
      border: 4px solid var(--text-primary);
      padding: 0;
      box-shadow: 12px 12px 0 var(--text-primary);
      overflow: hidden;
    }}
    form::before, .result::before {{
      content: "/// SYSTEM DIAGNOSTIC ///";
      display: block;
      background: var(--text-primary);
      color: var(--bg-color);
      padding: 10px 14px;
      font-family: "JetBrains Mono", monospace;
      font-weight: 900;
      letter-spacing: 0.08em;
      font-size: 0.78rem;
    }}
    form > * {{
      margin-left: 18px;
      margin-right: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
      margin-bottom: 18px;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-weight: 800;
      font-size: 0.9rem;
      font-family: "JetBrains Mono", monospace;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .span-2 {{ grid-column: span 2; }}
    input[type="text"], input[type="email"], select {{
      width: 100%;
      border: 2px solid var(--text-primary);
      padding: 11px 12px;
      font: inherit;
      background: #fff;
      color: var(--text-primary);
    }}
    .question {{
      border: 2px solid var(--text-primary);
      padding: 14px;
      margin: 0 0 10px;
      background: var(--surface-color);
    }}
    legend {{
      font-family: "Archivo Black", Impact, sans-serif;
      text-transform: uppercase;
      font-weight: 900;
      padding: 0 6px;
      letter-spacing: -0.02em;
    }}
    .scale-labels {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: var(--muted);
      font-size: 0.84rem;
      margin: 10px 0 4px;
      font-family: "JetBrains Mono", monospace;
      font-weight: 800;
      text-transform: uppercase;
    }}
    input[type="range"] {{ width: 100%; accent-color: var(--accent-red); }}
    button {{
      border: 0;
      background: var(--text-primary);
      color: white;
      font-family: "Archivo Black", Impact, sans-serif;
      text-transform: uppercase;
      letter-spacing: -0.02em;
      font-size: clamp(1.5rem, 4vw, 3rem);
      font-weight: 900;
      padding: 18px 16px;
      cursor: pointer;
      width: calc(100% - 36px);
      margin-bottom: 18px;
    }}
    button:hover {{ background: var(--accent-red); }}
    .result {{
      margin-top: 16px;
      display: none;
    }}
    .result h2 {{
      margin: 18px 18px 8px;
      font-family: "Archivo Black", Impact, sans-serif;
      text-transform: uppercase;
      font-size: clamp(2rem, 5vw, 4.4rem);
      line-height: 0.9;
      letter-spacing: -0.04em;
    }}
    .result > p {{ margin-left: 18px; margin-right: 18px; }}
    .result-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin: 14px 18px 18px;
    }}
    .result-panel {{
      border: 2px solid var(--text-primary);
      padding: 14px;
      background: var(--surface-color);
    }}
    .result-panel h3 {{
      margin: 0 0 8px;
      font-family: "JetBrains Mono", monospace;
      text-transform: uppercase;
      font-size: 0.9rem;
      color: var(--accent-red);
    }}
    ul {{ margin: 0; padding-left: 18px; color: var(--muted); }}
    li + li {{ margin-top: 5px; }}
    strong {{ color: var(--accent-red); }}
    .error {{
      color: var(--accent-red);
      font-weight: 800;
      min-height: 24px;
      margin-top: 10px;
      font-family: "JetBrains Mono", monospace;
      text-transform: uppercase;
    }}
    @media (max-width: 860px) {{
      header {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
      .span-2 {{ grid-column: auto; }}
      .result-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 520px) {{
      main {{ width: min(100% - 22px, 1060px); padding-top: 18px; }}
      form, .result {{ padding: 14px; }}
      nav {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main>
    <nav>
      <span>{config['brand']} diagnostic</span>
      <span><a href="/diagnostic?type=tbtx">TBTX</a> / <a href="/diagnostic?type=bizbuilders">BizBuilders AI</a></span>
    </nav>
    <header>
      <div>
        <div class="eyebrow">{config['audience']}</div>
        <h1>{config['title']}</h1>
      </div>
      <div class="brief">
        <p>{config['intro']}</p>
        <p>This maps your answers to the quad keystone: folders, markdowns, scripts, and protocols.</p>
      </div>
    </header>
    <form id="diagnostic-form">
      <div class="grid">
        <label>Name <input required name="name" type="text" autocomplete="name" /></label>
        <label>Email <input required name="email" type="email" autocomplete="email" /></label>
        <label>Company <input name="company" type="text" autocomplete="organization" /></label>
        <label>Role <input name="role" type="text" autocomplete="organization-title" /></label>
        <label class="span-2">Industry
          <select name="industry">
            <option value="">Choose one</option>
            <option>Creator / Personal Brand</option>
            <option>Consulting / Professional Services</option>
            <option>Agency / Marketing Services</option>
            <option>Ecommerce</option>
            <option>Health / Wellness / Aesthetics</option>
            <option>Local Business</option>
            <option>SaaS / Software</option>
            <option>Other</option>
          </select>
        </label>
      </div>
      {question_markup}
      <button type="submit">{config['cta']}</button>
      <div class="error" id="error"></div>
    </form>
    <section class="result" id="result" aria-live="polite"></section>
  </main>
  <script>
    const diagnosticType = "{diagnostic_type}";
    const source = "{config['source']}";
    const form = document.querySelector("#diagnostic-form");
    const result = document.querySelector("#result");
    const error = document.querySelector("#error");

    function list(items) {{
      return `<ul>${{items.map((item) => `<li>${{item}}</li>`).join("")}}</ul>`;
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      error.textContent = "";
      const data = new FormData(form);
      const params = new URLSearchParams(window.location.search);
      const answers = [...document.querySelectorAll(".question")].map((node) => {{
        const input = node.querySelector("input");
        return {{
          question_id: node.dataset.questionId,
          dimension: node.dataset.dimension,
          answer_value: Number(input.value),
          answer_label: node.querySelector("legend").textContent
        }};
      }});
      const payload = {{
        name: data.get("name"),
        email: data.get("email"),
        company: data.get("company") || "",
        role: data.get("role") || "",
        industry: data.get("industry") || "",
        diagnostic_type: diagnosticType,
        source,
        utm_source: params.get("utm_source") || "",
        utm_campaign: params.get("utm_campaign") || "",
        answers
      }};
      try {{
        const response = await fetch("/diagnostic/submit", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload)
        }});
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Submission failed");
        const topGaps = body.report.top_gaps.map((gap) =>
          `${{gap.label}} (${{Math.round(gap.severity * 100)}}% friction)`
        );
        result.style.display = "block";
        result.innerHTML = `
          <h2>${{body.report.headline}}</h2>
          <p><strong>Score:</strong> ${{body.score}} / ${{body.max_score}} | <strong>Category:</strong> ${{body.category}}</p>
          <p>${{body.report.summary}}</p>
          <div class="result-grid">
            <div class="result-panel">
              <h3>Industry Context</h3>
              <p>${{body.report.industry_context}}</p>
            </div>
            <div class="result-panel">
              <h3>Top Gaps</h3>
              ${{list(topGaps)}}
            </div>
            <div class="result-panel">
              <h3>Recommended Infrastructure</h3>
              ${{list(body.report.recommended_infrastructure)}}
            </div>
            <div class="result-panel">
              <h3>Phased Plan</h3>
              ${{list(body.report.phased_plan)}}
            </div>
          </div>
          <div class="result-panel" style="margin-top:14px">
            <h3>Highest Leverage Next Move</h3>
            <p>${{body.report.highest_leverage_next_move}}</p>
            <p><strong>Next CTA:</strong> ${{body.next_cta}} | <strong>Route:</strong> ${{body.route_to}}</p>
            <p><strong>Session:</strong> ${{body.session_id}}</p>
          </div>
        `;
        result.scrollIntoView({{ behavior: "smooth", block: "start" }});
      }} catch (err) {{
        error.textContent = err.message;
      }}
    }});
  </script>
</body>
</html>
"""


@app.post("/intake")
def intake(sub: Sub):
    task_id = "INTAKE-" + uuid.uuid4().hex[:12]
    gap_count = sum(1 for v in (sub.gaps or {}).values() if v > 0)
    labels = ["Stable system", "Targeted resource", "Infrastructure conversation", "Full engagement"]
    routing = sub.routing or labels[min(gap_count, 3)]
    envelope = {
        "task_id": task_id,
        "name": sub.name,
        "email": sub.email,
        "company": sub.company,
        "gaps": sub.gaps,
        "total_gaps": gap_count,
        "routing": routing,
        "friction": sub.friction,
        "stalling": sub.stalling,
        "answers": sub.answers,
        "source": sub.source,
        "created": datetime.datetime.utcnow().isoformat(),
    }
    pathlib.Path("/data/intake/" + task_id + ".json").write_text(json.dumps(envelope, indent=2))
    print("Intake received:", task_id, routing, flush=True)
    return {
        "status": "received",
        "task_id": task_id,
        "routing": routing,
        "message": "Baseline recorded. Observations within one business day.",
    }


@app.post("/diagnostic/submit")
def diagnostic_submit(sub: DiagnosticSub):
    config = get_config(sub.diagnostic_type)
    session_id = "DIAG-" + uuid.uuid4().hex[:12]
    score = sum(answer.answer_value for answer in sub.answers)
    max_score = len(sub.answers) * 5
    category = category_for(score, max_score)
    dimension_scores = score_dimensions(sub.answers)
    report = build_report(sub, category, dimension_scores)
    record = {
        "session_id": session_id,
        "lead": {
            "name": sub.name,
            "email": sub.email,
            "company": sub.company,
            "role": sub.role,
            "industry": sub.industry,
            "source": sub.source,
        },
        "diagnostic_type": sub.diagnostic_type,
        "score": score,
        "max_score": max_score,
        "category": category,
        "dimension_scores": dimension_scores,
        "report": report,
        "next_cta": config["cta"],
        "route_to": config["route_to"],
        "utm_source": sub.utm_source,
        "utm_campaign": sub.utm_campaign,
        "answers": [answer.model_dump() for answer in sub.answers],
        "created": datetime.datetime.utcnow().isoformat(),
    }
    pathlib.Path("/data/intake/" + session_id + ".json").write_text(json.dumps(record, indent=2))
    print("Diagnostic received:", session_id, sub.diagnostic_type, category, score, flush=True)
    return {
        "status": "received",
        "session_id": session_id,
        "score": score,
        "max_score": max_score,
        "category": category,
        "dimension_scores": dimension_scores,
        "report": report,
        "next_cta": config["cta"],
        "route_to": config["route_to"],
    }


@app.get("/intake/submissions")
def submissions(api_key: str = ""):
    if api_key != os.environ.get("WEBHOOK_API_KEY", ""):
        return {"error": "unauthorized"}
    files = sorted(pathlib.Path("/data/intake").glob("*.json"), reverse=True)
    return [json.loads(f.read_text()) for f in files[:20]]
