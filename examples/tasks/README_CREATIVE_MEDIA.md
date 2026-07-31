# Creative / media jobs (avoid markdown-only Hermes)

## What went wrong
`hermes --oneshot` is a **chat** path. It cannot invent mp4/png files.
Real assets come from `inputs.render_profile = tbtx_social_concepts_v1`, which runs
`scripts/render_tbtx_social_concepts.py` (ffmpeg + campaign source plates).

## Permanent guards (code)
1. **Intake** (`envelope_validation_service.normalize_creative_envelope_inputs`): media/creative jobs auto-receive `render_profile` + default `source_files`.
2. **Worker** (`queue_worker.resolve_creative_inputs` + `run_render_profile`): same auto-route; refuses chat-only completion when media is required.
3. **Contract check** (`runtime_output_validation.validate_artifact_contract`): completion fails if required video/image files are missing.

## Operator checklist
- Use `examples/tasks/tbtx_social_concepts_media.example.json` as the template.
- `source: manual`, `task_type: content_prep`, `risk_tier: reputation`, `owner_role: alpha`.
- Put media words in `output_required` (e.g. `mp4`, `video`, `contact sheet`).
- Prefer explicit `inputs.render_profile` and two `source_files` paths under `/workspace/source/campaign/`.
- Never expect Hermes chat to “generate” production video without a render profile.

## VPS source plates
Mounted at `/workspace/source/campaign/` on workers (host: `/opt/flow-as/runtime/agent-workspace/source/campaign/`).
