"""
FLOW Agent OS — Vercel entrypoint

Exposes a minimal FastAPI application for serverless deployment on Vercel.
Full multi-service features (Postgres, Redis, Ollama) require additional
external services; see the "Deploy to Vercel" section in README.md.
"""

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="FLOW Agent OS",
    version="1.0.0",
    description="FLOW Agent OS — Vercel serverless endpoint",
)


@app.get("/healthz")
def healthz():
    """Health-check endpoint — always returns 200 when the function is up."""
    return {
        "status": "ok",
        "openai_api_key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "openrouter_api_key_set": bool(os.environ.get("OPENROUTER_API_KEY")),
        "bizbrain_api_token_set": bool(os.environ.get("BIZBRAIN_API_TOKEN")),
    }


@app.get("/", response_class=HTMLResponse)
def index():
    """Basic index page confirming the deployment is live."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FLOW Agent OS</title>
  <style>
    body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, sans-serif;
           background: #f5f6f1; color: #172033; display: flex;
           align-items: center; justify-content: center; min-height: 100vh; }
    .card { background: #fff; border-radius: 12px; padding: 48px 56px;
            box-shadow: 0 4px 24px rgba(0,0,0,.08); max-width: 540px; text-align: center; }
    h1 { font-size: 2.4rem; margin: 0 0 12px; }
    p  { color: #596271; line-height: 1.6; }
    a  { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .badge { display: inline-block; background: #d1fae5; color: #065f46;
             border-radius: 99px; padding: 4px 14px; font-size: .85rem;
             font-weight: 600; margin-bottom: 20px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">&#10003; Deployed</div>
    <h1>FLOW Agent OS</h1>
    <p>Your Vercel deployment is live.</p>
    <p>
      Check <a href="/healthz">/healthz</a> for configuration status, or visit the
      <a href="https://github.com/erikhinla/flow-as" target="_blank" rel="noopener">
        GitHub repository
      </a> for full documentation.
    </p>
  </div>
</body>
</html>"""
