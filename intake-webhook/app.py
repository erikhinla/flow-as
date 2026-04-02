import uvicorn, json, os, pathlib, datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST","GET","OPTIONS"], allow_headers=["*"])
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

@app.get("/health")
def health():
    return {"status": "ok", "service": "flow-intake-webhook"}

@app.post("/intake")
def intake(sub: Sub):
    task_id = "INTAKE-" + datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    gap_count = sum(1 for v in (sub.gaps or {}).values() if v > 0)
    labels = ["Stable system", "Targeted resource", "Infrastructure conversation", "Full engagement"]
    routing = sub.routing or labels[min(gap_count, 3)]
    envelope = {
        "task_id": task_id, "name": sub.name, "email": sub.email,
        "company": sub.company, "gaps": sub.gaps, "total_gaps": gap_count,
        "routing": routing, "friction": sub.friction, "stalling": sub.stalling,
        "answers": sub.answers, "source": sub.source,
        "created": datetime.datetime.utcnow().isoformat()
    }
    pathlib.Path("/data/intake/" + task_id + ".json").write_text(json.dumps(envelope, indent=2))
    print("Intake received:", task_id, routing, flush=True)
    return {"status": "received", "task_id": task_id, "routing": routing,
            "message": "Baseline recorded. Observations within one business day."}

@app.get("/intake/submissions")
def submissions(api_key: str = ""):
    if api_key != os.environ.get("WEBHOOK_API_KEY", ""):
        return {"error": "unauthorized"}
    files = sorted(pathlib.Path("/data/intake").glob("*.json"), reverse=True)
    return [json.loads(f.read_text()) for f in files[:20]]
