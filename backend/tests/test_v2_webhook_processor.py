import unittest
from unittest.mock import ANY, patch

from app.services.v2_webhook_processor import process_v2_github_push


class V2WebhookProcessorTests(unittest.TestCase):
    def test_process_v2_github_push_stores_masked_detection_only(self):
        stored_payloads = []

        def fake_store(payloads):
            stored_payloads.extend(payloads)
            return [{"id": "detection-1"} for _ in payloads]

        with (
            patch(
                "app.services.v2_webhook_processor.get_installation_access_token",
                return_value={"token": "installation-token"},
            ),
            patch(
                "app.services.v2_webhook_processor.fetch_commit_diff_with_token",
                return_value={
                    "commit_sha": "abc123",
                    "files": [
                        {
                            "filename": "config.py",
                            "patch": '@@ -1,1 +1,1 @@\n+API_KEY = "sk_live_123456789abcdef"\n',
                        }
                    ],
                },
            ),
            patch(
                "app.services.v2_webhook_processor.analyze_secret_with_ai",
                return_value={
                    "is_risky": True,
                    "risk_level": "HIGH",
                    "confidence_score": 0.91,
                    "reason": "Looks like a live key",
                    "recommendation": "Rotate the key",
                },
            ),
            patch(
                "app.services.v2_webhook_processor.create_v2_detections_bulk",
                side_effect=fake_store,
            ),
            patch(
                "app.services.v2_webhook_processor.update_scan_event_status"
            ) as update_status,
        ):
            process_v2_github_push(
                scan_event={"id": "scan-event-1"},
                parsed_data={
                    "repo_full_name": "owner/repo",
                    "branch": "main",
                    "commit_shas": ["abc123"],
                },
                v2_repository={
                    "workspace_id": "workspace-1",
                    "repository_id": "repository-1",
                    "full_name": "owner/repo",
                    "github_installation_id": 12345,
                },
            )

        self.assertEqual(len(stored_payloads), 1)
        self.assertNotIn("raw_value", stored_payloads[0])
        self.assertEqual(stored_payloads[0]["masked_value"], "sk_l***************cdef")
        self.assertEqual(stored_payloads[0]["severity"], "high")
        self.assertEqual(stored_payloads[0]["scan_event_id"], "scan-event-1")
        update_status.assert_called_with(
            scan_event_id="scan-event-1",
            status="completed",
            completed_at=ANY,
        )

    def test_process_v2_github_push_marks_scan_event_failed_on_error(self):
        with (
            patch(
                "app.services.v2_webhook_processor.get_installation_access_token",
                side_effect=ValueError("missing token"),
            ),
            patch(
                "app.services.v2_webhook_processor.update_scan_event_status"
            ) as update_status,
        ):
            process_v2_github_push(
                scan_event={"id": "scan-event-1"},
                parsed_data={"repo_full_name": "owner/repo", "commit_shas": ["abc123"]},
                v2_repository={
                    "workspace_id": "workspace-1",
                    "repository_id": "repository-1",
                    "full_name": "owner/repo",
                    "github_installation_id": 12345,
                },
            )

        update_status.assert_called_with(
            scan_event_id="scan-event-1",
            status="failed",
            error_message="ValueError",
            completed_at=ANY,
        )


if __name__ == "__main__":
    unittest.main()
