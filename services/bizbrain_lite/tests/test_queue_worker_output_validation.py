import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.runtime_output_validation import (
    validate_artifact_contract,
    validate_runtime_output,
)


class RuntimeOutputValidationTests(unittest.TestCase):
    def test_accepts_finished_artifact(self) -> None:
        artifact = "# Finished\n\nThe requested Canon sentence is included."
        self.assertEqual(validate_runtime_output(artifact), artifact)

    def test_rejects_file_access_refusal(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "incomplete artifact"):
            validate_runtime_output(
                "It appears that I cannot access the file. Please provide the relevant text."
            )

    def test_rejects_missing_file_response(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "incomplete artifact"):
            validate_runtime_output(
                "The required file does not exist, so I am unable to retrieve its contents."
            )

    def test_rejects_varied_missing_file_response(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "incomplete artifact"):
            validate_runtime_output(
                "The file does not exist in the specified path, and I am unable to return it."
            )

    def test_rejects_tool_failure_artifact(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "incomplete artifact"):
            validate_runtime_output(
                "I encountered an issue while trying to access the file. "
                "It does not exist and permission restrictions are preventing access.\n\n"
                "⚠️ Write failed"
            )

    def test_rejects_empty_artifact(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "empty artifact"):
            validate_runtime_output("  \n")

    def test_media_contract_rejects_markdown_plan_without_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "expected 3 rendered video"):
                validate_artifact_contract(
                    "Three rendered 1920x1080 17-second videos, a contact sheet, "
                    "a transparent wordmark PNG, and a validation report.",
                    Path(directory),
                )

    @patch(
        "app.services.runtime_output_validation._probe_video",
        return_value={"width": 1920, "height": 1080, "duration": 17.0, "has_audio": True},
    )
    def test_media_contract_accepts_real_file_set(self, _probe) -> None:
        transparent_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
            "AAAADUlEQVR42mNk+M/wHwAF/gL+Xnw6WQAAAABJRU5ErkJggg=="
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(1, 4):
                (root / f"concept-{index}.mp4").write_bytes(b"real-video-placeholder")
            (root / "concept-contact-sheet.png").write_bytes(transparent_png)
            (root / "tbtx-wordmark.png").write_bytes(transparent_png)
            (root / "validation-report.md").write_text("# Validation\nPassed.", encoding="utf-8")

            files = validate_artifact_contract(
                "Three rendered 1920x1080 17-second videos, a contact sheet, "
                "a transparent wordmark PNG, and a validation report.",
                root,
            )

        self.assertEqual(len(files), 6)

    @patch(
        "app.services.runtime_output_validation._probe_video",
        return_value={"width": 1280, "height": 720, "duration": 10.0, "has_audio": False},
    )
    def test_media_contract_rejects_wrong_video_spec(self, _probe) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "concept.mp4").write_bytes(b"not-empty")
            with self.assertRaisesRegex(RuntimeError, "expected 1920x1080"):
                validate_artifact_contract(
                    "One rendered 1920x1080 17-second video.",
                    root,
                )


if __name__ == "__main__":
    unittest.main()
