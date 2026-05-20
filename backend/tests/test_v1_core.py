import hashlib
import hmac
import unittest

from app.services.github_service import extract_added_lines
from app.services.scanner_service import scan_added_lines, scan_line_for_secrets
from app.utils.github_payload import parse_push_payload
from app.utils.masking import mask_secret
from app.utils.signature import verify_github_signature


class V1CoreTests(unittest.TestCase):
    def test_signature_verification(self):
        body = b'{"zen":"Keep it logically awesome."}'
        secret = "test-secret"
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        self.assertTrue(
            verify_github_signature(body, f"sha256={digest}", secret)
        )
        self.assertFalse(verify_github_signature(body, "", secret))
        self.assertFalse(verify_github_signature(body, "sha256=wrong", secret))

    def test_payload_parsing_uses_safe_defaults(self):
        parsed = parse_push_payload(
            {
                "ref": "refs/heads/main",
                "repository": {
                    "full_name": "owner/repo",
                    "name": "repo",
                    "owner": {"login": "owner"},
                },
                "pusher": {"name": "dev", "email": "dev@example.com"},
                "head_commit": {"id": "abc123"},
                "commits": [
                    {
                        "id": "abc123",
                        "message": "test",
                        "added": ["config.py"],
                        "modified": ["app.py"],
                        "removed": ["old.py"],
                    }
                ],
            }
        )

        self.assertEqual(parsed["repo_full_name"], "owner/repo")
        self.assertEqual(parsed["branch"], "main")
        self.assertEqual(parsed["commit_count"], 1)
        self.assertEqual(parsed["commit_shas"], ["abc123"])
        self.assertEqual(parsed["added_files"], ["config.py"])
        self.assertEqual(parsed["modified_files"], ["app.py"])
        self.assertEqual(parsed["removed_files"], ["old.py"])

    def test_extract_added_lines_ignores_removed_and_metadata(self):
        added_lines = extract_added_lines(
            [
                {
                    "filename": "config.py",
                    "patch": (
                        "@@ -1,3 +10,4 @@\n"
                        " context line\n"
                        "-PASSWORD = old\n"
                        "+API_KEY = \"abc123XYZ789token\"\n"
                        "+DEBUG = False\n"
                        "+++ b/config.py\n"
                    ),
                }
            ]
        )

        self.assertEqual(len(added_lines), 2)
        self.assertEqual(added_lines[0]["line_number"], 11)
        self.assertEqual(added_lines[0]["line_content"], 'API_KEY = "abc123XYZ789token"')
        self.assertEqual(added_lines[1]["line_number"], 12)

    def test_regex_scanner_detects_common_secrets(self):
        samples = [
            'GITHUB_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz123456"',
            'API_KEY = "sk_live_123456789abcdef"',
            'PASSWORD = "supersecret123"',
            'DATABASE_URL = "postgres://user:pass@localhost:5432/db"',
            'AUTH_HEADER = "Bearer abcdef1234567890"',
            'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"',
        ]

        for sample in samples:
            with self.subTest(sample=sample):
                self.assertTrue(scan_line_for_secrets(sample))

    def test_entropy_scanner_detects_random_assignment(self):
        detections = scan_line_for_secrets(
            'CUSTOM_API_KEY = "x7k9mP2qL5nR8wT3vB6jD4fG1hS0aZ"'
        )

        self.assertTrue(
            any(
                detection["secret_type"] == "high_entropy_string"
                for detection in detections
            )
        )

    def test_scanner_attaches_masked_value_not_only_raw_value(self):
        detections = scan_added_lines(
            [
                {
                    "file_path": "config.py",
                    "line_number": 5,
                    "line_content": 'API_KEY = "sk_live_123456789abcdef"',
                }
            ]
        )

        self.assertEqual(detections[0]["line_number"], 5)
        self.assertIn("raw_value", detections[0])
        self.assertIn("masked_value", detections[0])
        self.assertNotEqual(detections[0]["raw_value"], detections[0]["masked_value"])

    def test_masking(self):
        self.assertEqual(mask_secret("sk_live_123456789abcdef"), "sk_l***************cdef")


if __name__ == "__main__":
    unittest.main()
