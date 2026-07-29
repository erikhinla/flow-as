import asyncio
import json
from pathlib import Path

from app.workers.queue_worker import build_execution_prompt, write_output


def test_execution_prompt_binds_workspace_and_output_contract(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    prompt = asyncio.run(
        build_execution_prompt(
            goal="Create the approved creative concept.",
            title="Creative proof",
            task_type="content_prep",
            owner="alpha",
            output_required="One rendered 1920x1080 17-second MP4.",
            inputs={"files": ["source.mov"]},
            job_workspace=workspace,
        )
    )

    assert str(workspace) in prompt
    assert "One rendered 1920x1080 17-second MP4." in prompt
    assert "create those real files" in prompt
    assert "do not return a plan" in prompt.lower()


def test_write_output_stages_real_files_and_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    produced = workspace / "concept.mp4"
    produced.write_bytes(b"rendered-media")
    output_root = tmp_path / "reviews"

    output_path = write_output(
        job_id="job-123",
        title="Creative proof",
        owner="alpha",
        engine="hermes",
        content="Created concept.mp4.",
        output_base=str(output_root),
        job_workspace=workspace,
        produced_files=[produced],
        runtime_evidence={"workflow_stages": ["agent_zero", "openclaw"]},
    )

    staged = output_root / "job-123" / "files" / "concept.mp4"
    metadata = json.loads((output_root / "job-123" / "metadata.json").read_text())
    assert Path(output_path).is_file()
    assert staged.read_bytes() == b"rendered-media"
    assert metadata["artifacts"][0]["relative_path"] == "concept.mp4"
