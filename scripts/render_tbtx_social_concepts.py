#!/usr/bin/env python3
"""Render three review-stage TBTX social concepts from existing campaign footage."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


DURATION = 17
WIDTH = 1920
HEIGHT = 1080
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
)


def run(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            (completed.stderr or completed.stdout or "command failed")[-4_000:]
        )


def font_path() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError("No supported display font is installed in the renderer image")


def write_copy_files(workspace: Path) -> dict[str, Path]:
    values = {
        "hook": "You’re not imagining it.",
        "support": "More output created more to manage.",
        "cta": "FIND OUT WHY",
        "url": "transformby10x.ai/diagnostic",
        "wordmark": "TransformBy10X",
    }
    paths: dict[str, Path] = {}
    for key, value in values.items():
        path = workspace / f"{key}.txt"
        path.write_text(value, encoding="utf-8")
        paths[key] = path
    return paths


def drawtext(
    *,
    font: str,
    textfile: Path,
    size: int,
    color: str,
    x: str,
    y: str,
    enable: str,
    alpha: str = "1",
) -> str:
    return (
        f"drawtext=fontfile='{font}':textfile='{textfile}':"
        f"fontsize={size}:fontcolor={color}:x={x}:y={y}:"
        f"alpha='{alpha}':enable='{enable}'"
    )


def render_wordmark(workspace: Path, copy: dict[str, Path], font: str) -> Path:
    output = workspace / "transformby10x-wordmark-transparent.png"
    filter_graph = (
        "format=rgba,"
        + drawtext(
            font=font,
            textfile=copy["wordmark"],
            size=112,
            color="white",
            x="40",
            y="52",
            enable="1",
        )
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black@0.0:s=1100x220:d=1",
            "-vf",
            filter_graph,
            "-frames:v",
            "1",
            output.as_posix(),
        ]
    )
    return output


def audio_filter(kind: str) -> str:
    if kind == "pressure":
        return (
            "aevalsrc='0.018*sin(2*PI*58*t)+"
            "0.012*sin(2*PI*116*t)*(1-between(t,6.0,7.0))+"
            "0.035*sin(2*PI*92*t)*gte(t,7)*lt(mod(t-7,0.5),0.11)':"
            "s=48000:d=17"
        )
    if kind == "warm":
        return (
            "aevalsrc='0.016*sin(2*PI*196*t)+0.010*sin(2*PI*293.66*t)+"
            "0.018*sin(2*PI*73*t)*lt(mod(t,1.0),0.16)':s=48000:d=17"
        )
    return (
        "aevalsrc='0.014*sin(2*PI*82*t)+0.010*sin(2*PI*164*t)+"
        "0.028*sin(2*PI*740*t)*lt(mod(t,0.5),0.035)':s=48000:d=17"
    )


def render_concept(
    *,
    name: str,
    source: Path,
    output: Path,
    font: str,
    copy: dict[str, Path],
    treatment: str,
) -> None:
    base = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,fps=30,"
    )
    if treatment == "pressure":
        visual = (
            base
            + "eq=brightness=-0.12:contrast=1.18:saturation=0.72,"
            "gblur=sigma=5,"
            "drawbox=x=0:y=0:w=1220:h=1080:color=0x07131a@0.88:t=fill,"
            "drawbox=x='1180+40*sin(t*1.8)':y=0:w=740:h=1080:"
            "color=0x09161d@0.18:t=fill,"
        )
        accent = "0x62E6A8"
        hook_x, hook_y = "96", "220"
    elif treatment == "warm":
        visual = (
            base
            + "eq=brightness=-0.08:contrast=1.10:saturation=0.82:"
            "gamma_r=1.06:gamma_b=0.92,"
            "drawbox=x=0:y=650:w=1920:h=430:color=0x111312@0.82:t=fill,"
        )
        accent = "0xE7B98B"
        hook_x, hook_y = "110", "700"
    else:
        visual = (
            base
            + "eq=brightness=-0.10:contrast=1.24:saturation=0.62:"
            "gamma_b=1.08,"
            "drawbox=x=0:y=0:w=760:h=1080:color=0x071019@0.90:t=fill,"
            "drawbox=x=760:y=0:w=8:h=1080:color=0x8D7CFF@0.72:t=fill,"
        )
        accent = "0x9A8CFF"
        hook_x, hook_y = "86", "180"

    filters = [
        visual.rstrip(","),
        drawtext(
            font=font,
            textfile=copy["hook"],
            size=84,
            color="white",
            x=hook_x,
            y=hook_y,
            enable="between(t,0.5,6.2)",
            alpha="min(1,max(0,(t-0.5)/0.55))*min(1,max(0,(6.2-t)/0.45))",
        ),
        drawtext(
            font=font,
            textfile=copy["support"],
            size=48,
            color=accent,
            x=hook_x,
            y=f"{hook_y}+150",
            enable="between(t,5.2,11.8)",
            alpha="min(1,max(0,(t-5.2)/0.5))*min(1,max(0,(11.8-t)/0.5))",
        ),
        "drawbox=x=86:y=824:w='min(540,max(0,(t-11.2)*170))':h=5:"
        f"color={accent}@0.88:t=fill:enable='between(t,11.2,16.8)'",
        drawtext(
            font=font,
            textfile=copy["cta"],
            size=62,
            color="white",
            x="86",
            y="854",
            enable="between(t,11.5,17)",
            alpha="min(1,max(0,(t-11.5)/0.45))",
        ),
        drawtext(
            font=font,
            textfile=copy["url"],
            size=34,
            color=accent,
            x="86",
            y="946",
            enable="between(t,12.0,17)",
            alpha="min(1,max(0,(t-12.0)/0.45))",
        ),
        "format=yuv420p",
    ]

    run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            source.as_posix(),
            "-f",
            "lavfi",
            "-i",
            audio_filter(treatment),
            "-filter_complex",
            f"[0:v]{','.join(filters)}[v];[1:a]afade=t=in:st=0:d=0.35,"
            "afade=t=out:st=16.2:d=0.8[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            str(DURATION),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            output.as_posix(),
        ]
    )


def render_contact_sheet(videos: list[Path], workspace: Path) -> Path:
    output = workspace / "concept-contact-sheet.png"
    command = ["ffmpeg", "-y"]
    for video in videos:
        command.extend(["-ss", "5", "-i", video.as_posix()])
    command.extend(
        [
            "-filter_complex",
            "[0:v]scale=640:360[a];[1:v]scale=640:360[b];"
            "[2:v]scale=640:360[c];[a][b][c]hstack=inputs=3[out]",
            "-map",
            "[out]",
            "-frames:v",
            "1",
            output.as_posix(),
        ]
    )
    run(command)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--source-a", required=True)
    parser.add_argument("--source-b", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    source_a = Path(args.source_a).resolve()
    source_b = Path(args.source_b).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    for source in (source_a, source_b):
        if not source.is_file():
            raise RuntimeError(f"Source video not found: {source}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe are required")

    font = font_path()
    copy = write_copy_files(workspace)
    wordmark = render_wordmark(workspace, copy, font)
    videos = [
        workspace / "concept-a-pressure-space-momentum.mp4",
        workspace / "concept-b-warm-human.mp4",
        workspace / "concept-c-future-forward.mp4",
    ]
    render_concept(
        name="Concept A",
        source=source_a,
        output=videos[0],
        font=font,
        copy=copy,
        treatment="pressure",
    )
    render_concept(
        name="Concept B",
        source=source_b,
        output=videos[1],
        font=font,
        copy=copy,
        treatment="warm",
    )
    render_concept(
        name="Concept C",
        source=source_a,
        output=videos[2],
        font=font,
        copy=copy,
        treatment="future",
    )
    contact_sheet = render_contact_sheet(videos, workspace)
    manifest = {
        "profile": "tbtx_social_concepts_v1",
        "status": "staged_for_review",
        "videos": [path.name for path in videos],
        "wordmark": wordmark.name,
        "contact_sheet": contact_sheet.name,
        "published": False,
    }
    (workspace / "render-manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
