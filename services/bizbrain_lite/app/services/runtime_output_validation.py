from __future__ import annotations

import re
import struct
import subprocess
import json
from pathlib import Path


INCOMPLETE_OUTPUT_MARKERS: tuple[str, ...] = (
    "i cannot access",
    "i can't access",
    "i encountered an issue",
    "i am unable to access",
    "i'm currently unable to access",
    "i am unable to complete",
    "i'm unable to complete",
    "i cannot complete",
    "i can't complete",
    "i am unable to retrieve",
    "i'm unable to retrieve",
    "not able to complete",
    "not able to fulfill",
    "not available in the system",
    "does not exist, so i am unable",
    "preventing access",
    "please provide the relevant text",
)

MEDIA_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".webm",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
}


def requires_media_artifacts(output_required: str | None) -> bool:
    contract = " ".join((output_required or "").strip().lower().split())
    return any(
        token in contract
        for token in (
            "video",
            "rendered",
            "mp4",
            "mov",
            "image",
            "contact sheet",
            "audio",
            "sound design",
        )
    )


def _requested_count(text: str, noun: str, default: int = 1) -> int:
    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
    }
    pattern = rf"\b(one|two|three|four|five|six|\d+)\b[^.\n]{{0,80}}\b{noun}s?\b"
    match = re.search(pattern, text)
    if not match:
        return default
    raw = match.group(1)
    return number_words.get(raw, int(raw) if raw.isdigit() else default)


def _is_transparent_png(path: Path) -> bool:
    """Check the PNG IHDR color type without requiring an image library."""
    try:
        with path.open("rb") as handle:
            signature = handle.read(8)
            if signature != b"\x89PNG\r\n\x1a\n":
                return False
            length = struct.unpack(">I", handle.read(4))[0]
            chunk_type = handle.read(4)
            data = handle.read(length)
        return chunk_type == b"IHDR" and len(data) >= 10 and data[9] in {4, 6}
    except (OSError, struct.error):
        return False


def _workspace_files(workspace: Path) -> list[Path]:
    if not workspace.is_dir():
        return []
    return sorted(
        path
        for path in workspace.rglob("*")
        if path.is_file() and not path.is_symlink() and not path.name.startswith(".")
    )


def _probe_video(path: Path) -> dict[str, float | int]:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,width,height:format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        payload = json.loads(completed.stdout)
        streams = payload.get("streams") or []
        stream = next(
            (item for item in streams if item.get("codec_type") == "video"),
            {},
        )
        return {
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
            "duration": float((payload.get("format") or {}).get("duration") or 0),
            "has_audio": any(item.get("codec_type") == "audio" for item in streams),
        }
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"unreadable video file {path.name}: {exc}") from exc


def validate_runtime_output(content: str) -> str:
    """Reject empty or plainly incomplete agent artifacts before completion."""
    normalized = " ".join(content.strip().lower().split())
    if not normalized:
        raise RuntimeError("Agent returned an empty artifact")

    opening = normalized[:1_200]
    marker = next((value for value in INCOMPLETE_OUTPUT_MARKERS if value in opening), None)
    missing_source_refusal = (
        any(value in opening for value in ("does not exist", "not found", "no such file"))
        and any(
            value in opening
            for value in ("unable to", "cannot", "can't", "preventing", "encountered an issue", "failed")
        )
    )
    failed_tool_call = "⚠️" in content and "failed" in opening
    if marker or missing_source_refusal or failed_tool_call:
        detected = marker or (
            "failed tool call" if failed_tool_call else "missing source and unable to complete"
        )
        raise RuntimeError(
            "Agent returned an incomplete artifact instead of the requested result "
            f"(detected: {detected})"
        )
    return content.strip()


def validate_artifact_contract(
    output_required: str | None,
    workspace: Path,
    *,
    pre_review: bool = False,
) -> list[Path]:
    """Reject a claimed completion when required production files do not exist.

    The task's observable output contract is authoritative. A prose response is
    never accepted as a substitute for requested video, image, audio, or report
    files. Each job receives an isolated workspace so files found here were
    created for this job rather than inherited from an earlier run.
    """
    contract = " ".join((output_required or "").strip().lower().split())
    if not contract:
        return []

    files = _workspace_files(workspace)
    video_files = [path for path in files if path.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"}]
    image_files = [path for path in files if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}]
    audio_files = [path for path in files if path.suffix.lower() in {".wav", ".mp3", ".m4a", ".aac"}]
    report_files = [
        path
        for path in files
        if path.suffix.lower() in {".md", ".json", ".txt", ".html"}
        and any(word in path.stem.lower() for word in ("validation", "report", "qc", "readme"))
    ]

    errors: list[str] = []
    requested_media = requires_media_artifacts(contract)

    if any(token in contract for token in ("video", "rendered video", "mp4", "mov")):
        expected = _requested_count(contract, "video")
        if len(video_files) < expected:
            errors.append(f"expected {expected} rendered video file(s), found {len(video_files)}")
        else:
            resolution_match = re.search(r"\b(\d{3,4})\s*[x×]\s*(\d{3,4})\b", contract)
            duration_match = re.search(r"\b(\d+(?:\.\d+)?)\s*[- ]?\s*seconds?\b", contract)
            for video_path in video_files[:expected]:
                try:
                    probe = _probe_video(video_path)
                except RuntimeError as exc:
                    errors.append(str(exc))
                    continue
                if resolution_match:
                    expected_width = int(resolution_match.group(1))
                    expected_height = int(resolution_match.group(2))
                    if (
                        probe["width"] != expected_width
                        or probe["height"] != expected_height
                    ):
                        errors.append(
                            f"{video_path.name} is {probe['width']}x{probe['height']}, "
                            f"expected {expected_width}x{expected_height}"
                        )
                if duration_match:
                    expected_duration = float(duration_match.group(1))
                    if abs(float(probe["duration"]) - expected_duration) > 0.35:
                        errors.append(
                            f"{video_path.name} is {probe['duration']:.2f}s, "
                            f"expected {expected_duration:.2f}s"
                        )
                if any(token in contract for token in ("sound", "audio", "song", "music")):
                    if not bool(probe.get("has_audio")):
                        errors.append(f"{video_path.name} has no audio stream")

    if (
        any(token in contract for token in ("contact sheet", "contact-sheet"))
        and not any("contact" in path.stem.lower() for path in image_files)
    ):
        errors.append("expected a contact-sheet image, found none")

    transparent_mark_requested = bool(
        re.search(
            r"\btransparent\b(?:\s+\w+){0,4}\s+\b(?:wordmark|logo)\b",
            contract,
        )
    )
    if transparent_mark_requested:
        transparent_marks = [
            path
            for path in image_files
            if path.suffix.lower() == ".png"
            and any(word in path.stem.lower() for word in ("logo", "wordmark"))
            and _is_transparent_png(path)
        ]
        if not transparent_marks:
            errors.append("expected a transparent PNG logo or wordmark, found none")

    if any(token in contract for token in ("audio file", "sound design file", "sound file")) and not audio_files:
        errors.append("expected an audio file, found none")

    if not pre_review and "validation report" in contract and not report_files:
        errors.append("expected a validation report file, found none")

    if requested_media:
        empty_media = [path for path in files if path.suffix.lower() in MEDIA_EXTENSIONS and path.stat().st_size == 0]
        if empty_media:
            errors.append(
                "empty media file(s): " + ", ".join(path.name for path in empty_media[:5])
            )

    if errors:
        raise RuntimeError(
            "Completion gate failed: "
            + "; ".join(errors)
            + f". Required files must be created under {workspace}."
        )

    return files
