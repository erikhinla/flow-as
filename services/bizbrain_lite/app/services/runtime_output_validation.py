INCOMPLETE_OUTPUT_MARKERS: tuple[str, ...] = (
    "i cannot access",
    "i can't access",
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
    "please provide the relevant text",
)


def validate_runtime_output(content: str) -> str:
    """Reject empty or plainly incomplete agent artifacts before completion."""
    normalized = " ".join(content.strip().lower().split())
    if not normalized:
        raise RuntimeError("Agent returned an empty artifact")

    opening = normalized[:1_200]
    marker = next((value for value in INCOMPLETE_OUTPUT_MARKERS if value in opening), None)
    if marker:
        raise RuntimeError(
            "Agent returned an incomplete artifact instead of the requested result "
            f"(detected: {marker})"
        )
    return content.strip()
