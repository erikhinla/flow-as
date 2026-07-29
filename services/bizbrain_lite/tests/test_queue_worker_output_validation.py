import unittest

from app.services.runtime_output_validation import validate_runtime_output


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


if __name__ == "__main__":
    unittest.main()
