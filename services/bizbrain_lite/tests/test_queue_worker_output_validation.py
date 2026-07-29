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

    def test_rejects_empty_artifact(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "empty artifact"):
            validate_runtime_output("  \n")


if __name__ == "__main__":
    unittest.main()
