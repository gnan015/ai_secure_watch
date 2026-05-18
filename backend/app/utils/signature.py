import hashlib
import hmac


def verify_github_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """Verify GitHub's X-Hub-Signature-256 header."""
    if not payload_body or not signature_header or not secret:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    expected_header = f"sha256={expected_signature}"
    return hmac.compare_digest(expected_header, signature_header)
