import re

from app.utils.entropy import calculate_entropy, is_high_entropy
from app.utils.masking import mask_secret


# Each regex has one capture group for the actual secret value.
SECRET_PATTERNS = [
    {
        "secret_type": "github_token",
        "pattern": re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b"),
        "confidence_hint": "high",
    },
    {
        "secret_type": "api_key",
        "pattern": re.compile(
            r"""\b(?:api[_-]?key|apikey|secret[_-]?key|client[_-]?secret)\b\s*[:=]\s*["']?([^"'\s,;]{6,})""",
            re.IGNORECASE,
        ),
        "confidence_hint": "medium",
    },
    {
        "secret_type": "password",
        "pattern": re.compile(
            r"""\b(?:password|passwd|pwd)\b\s*[:=]\s*["']?([^"'\s,;]{4,})""",
            re.IGNORECASE,
        ),
        "confidence_hint": "medium",
    },
    {
        "secret_type": "database_url",
        "pattern": re.compile(
            r"""\b((?:postgresql|postgres|mysql|mongodb|redis|mssql|sqlserver)://[^\s"']+)""",
            re.IGNORECASE,
        ),
        "confidence_hint": "high",
    },
    {
        "secret_type": "jwt_token",
        "pattern": re.compile(
            r"\b(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b"
        ),
        "confidence_hint": "high",
    },
    {
        "secret_type": "private_key",
        "pattern": re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----)"),
        "confidence_hint": "high",
    },
    {
        "secret_type": "aws_access_key",
        "pattern": re.compile(r"\b((?:AKIA|ASIA)[A-Z0-9]{16})\b"),
        "confidence_hint": "high",
    },
    {
        "secret_type": "bearer_token",
        "pattern": re.compile(
            r"""\bbearer\s+([A-Za-z0-9._~+/=-]{10,})""",
            re.IGNORECASE,
        ),
        "confidence_hint": "medium",
    },
]


ASSIGNMENT_VALUE_PATTERN = re.compile(
    r"""\b[A-Za-z_][A-Za-z0-9_]*(?:key|token|secret|password|passwd|pwd|auth|credential)[A-Za-z0-9_]*\b\s*[:=]\s*["']?([^"'\s,;]+)""",
    re.IGNORECASE,
)
QUOTED_VALUE_PATTERN = re.compile(r"""["']([^"']{16,})["']""")


def _is_entropy_candidate(value: str) -> bool:
    """Decide whether a string is worth checking with entropy."""
    if len(value) < 16:
        return False

    if "://" in value or value.lower().startswith(("http://", "https://")):
        return False

    if any(character.isspace() for character in value):
        return False

    has_letter = any(character.isalpha() for character in value)
    has_number = any(character.isdigit() for character in value)

    if not has_letter or not has_number:
        return False

    return True


def _find_entropy_candidates(line_content: str) -> list:
    """Find quoted or assignment values that might contain secret material."""
    candidates = []

    for pattern in (ASSIGNMENT_VALUE_PATTERN, QUOTED_VALUE_PATTERN):
        for match in pattern.finditer(line_content):
            candidate = match.group(1).strip()

            if _is_entropy_candidate(candidate) and candidate not in candidates:
                candidates.append(candidate)

    return candidates


def scan_line_for_secrets(line_content: str) -> list:
    """Scan one added line with regex and entropy-based detection."""
    detections = []

    for secret_pattern in SECRET_PATTERNS:
        for match in secret_pattern["pattern"].finditer(line_content):
            raw_value = match.group(1)

            detections.append(
                {
                    "secret_type": secret_pattern["secret_type"],
                    "raw_value": raw_value,
                    "confidence_hint": secret_pattern["confidence_hint"],
                    "detection_method": "regex",
                }
            )

    regex_values = {detection["raw_value"] for detection in detections}

    # High entropy means a value looks random. That can be suspicious because
    # many tokens and API keys are intentionally random. Entropy alone is not
    # proof of a real secret, so a later Gemini phase can add smarter review.
    for candidate in _find_entropy_candidates(line_content):
        if candidate in regex_values:
            continue

        entropy_score = calculate_entropy(candidate)

        if is_high_entropy(candidate):
            detections.append(
                {
                    "secret_type": "high_entropy_string",
                    "raw_value": candidate,
                    "masked_value": mask_secret(candidate),
                    "confidence_hint": "medium",
                    "detection_method": "entropy",
                    "entropy_score": round(entropy_score, 2),
                }
            )

    return detections


def scan_added_lines(added_lines: list) -> list:
    """Scan GitHub diff added lines and attach file metadata to detections."""
    detected_secrets = []

    for added_line in added_lines:
        line_content = added_line.get("line_content", "")
        line_detections = scan_line_for_secrets(line_content)

        for detection in line_detections:
            raw_value = detection["raw_value"]

            detected_secrets.append(
                {
                    "file_path": added_line.get("file_path", "unknown"),
                    "line_number": added_line.get("line_number"),
                    "line_content": line_content,
                    "secret_type": detection["secret_type"],
                    "raw_value": raw_value,
                    "masked_value": detection.get(
                        "masked_value", mask_secret(raw_value)
                    ),
                    "confidence_hint": detection["confidence_hint"],
                    "detection_method": detection["detection_method"],
                    **(
                        {"entropy_score": detection["entropy_score"]}
                        if "entropy_score" in detection
                        else {}
                    ),
                }
            )

    return detected_secrets
