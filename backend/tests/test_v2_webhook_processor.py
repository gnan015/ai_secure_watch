import unittest
from unittest.mock import ANY, patch

from app.services.database_service import (
    DatabaseError,
    create_v2_detections_bulk,
)
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
        self.assertEqual(
            set(stored_payloads[0].keys()),
            {
                "workspace_id",
                "repository_id",
                "scan_event_id",
                "repo_full_name",
                "branch",
                "commit_sha",
                "file_path",
                "line_number",
                "secret_type",
                "masked_value",
                "detection_method",
                "entropy_score",
                "severity",
                "confidence_score",
                "ai_reasoning",
                "ai_recommendation",
                "status",
            },
        )
        self.assertNotIn("raw_value", stored_payloads[0])
        self.assertNotIn("raw_secret", stored_payloads[0])
        self.assertNotIn("secret_value", stored_payloads[0])
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
            error_message="ValueError: missing token",
            completed_at=ANY,
        )

    def test_process_v2_github_push_marks_scan_event_failed_when_insert_fails(self):
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
                side_effect=DatabaseError("insert failed"),
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

        update_status.assert_called_with(
            scan_event_id="scan-event-1",
            status="failed",
            error_message="DatabaseError: insert failed",
            completed_at=ANY,
        )

    def test_create_v2_detections_bulk_filters_raw_secret_fields(self):
        captured_payloads = []

        def fake_table_request(table_name, method, payload=None, **_):
            captured_payloads.extend(payload)
            return [{"id": "detection-1"}]

        with patch(
            "app.services.database_service._send_supabase_table_request",
            side_effect=fake_table_request,
        ):
            create_v2_detections_bulk(
                [
                    {
                        "workspace_id": "workspace-1",
                        "repository_id": "repository-1",
                        "scan_event_id": "scan-event-1",
                        "repo_full_name": "owner/repo",
                        "branch": "main",
                        "commit_sha": "abc123",
                        "file_path": "config.py",
                        "line_number": 1,
                        "secret_type": "api_key",
                        "masked_value": "sk_l***************cdef",
                        "detection_method": "regex",
                        "entropy_score": None,
                        "severity": "high",
                        "confidence_score": 0.91,
                        "ai_reasoning": "Looks like a live key",
                        "ai_recommendation": "Rotate the key",
                        "status": "open",
                        "raw_value": "sk_live_123456789abcdef",
                        "raw_secret": "sk_live_123456789abcdef",
                        "secret_value": "sk_live_123456789abcdef",
                    }
                ]
            )

        self.assertEqual(len(captured_payloads), 1)
        self.assertNotIn("raw_value", captured_payloads[0])
        self.assertNotIn("raw_secret", captured_payloads[0])
        self.assertNotIn("secret_value", captured_payloads[0])
        self.assertEqual(captured_payloads[0]["masked_value"], "sk_l***************cdef")


if __name__ == "__main__":
    unittest.main()
