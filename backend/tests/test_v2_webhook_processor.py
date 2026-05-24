import unittest
from unittest.mock import ANY, Mock, patch

from app.services.database_service import (
    DatabaseError,
    create_v2_detections_bulk,
)
from app.services.discord_webhook_service import (
    DiscordWebhookServiceError,
    send_detection_alert,
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
                "app.services.v2_webhook_processor.list_enabled_discord_webhooks_for_workspace",
                return_value=[],
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
            error_message="ValueError",
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
                "app.services.v2_webhook_processor.list_enabled_discord_webhooks_for_workspace"
            ) as list_webhooks,
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
        list_webhooks.assert_not_called()

    def test_process_v2_github_push_sends_discord_alert_for_enabled_workspace_webhook(self):
        sent_detections = []

        def fake_send(_webhook_url, detection):
            sent_detections.append(detection)

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
                return_value=[{"id": "detection-1"}],
            ),
            patch(
                "app.services.v2_webhook_processor.list_enabled_discord_webhooks_for_workspace",
                return_value=[
                    {
                        "id": "webhook-1",
                        "workspace_id": "workspace-1",
                        "webhook_url_ciphertext": "ciphertext",
                    }
                ],
            ) as list_webhooks,
            patch(
                "app.services.v2_webhook_processor.decrypt_webhook_url",
                return_value="https://discord.com/api/webhooks/secret",
            ),
            patch(
                "app.services.v2_webhook_processor.send_detection_alert",
                side_effect=fake_send,
            ) as send_alert,
            patch(
                "app.services.v2_webhook_processor.update_discord_webhook_alert_status"
            ) as update_alert_status,
            patch("app.services.v2_webhook_processor.update_scan_event_status"),
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

        list_webhooks.assert_called_once_with("workspace-1")
        send_alert.assert_called_once()
        update_alert_status.assert_called_with(
            workspace_id="workspace-1",
            webhook_id="webhook-1",
            last_error=None,
        )
        self.assertEqual(sent_detections[0]["masked_value"], "sk_l***************cdef")
        self.assertNotIn("raw_value", sent_detections[0])
        self.assertNotIn("raw_secret", sent_detections[0])
        self.assertNotIn("secret_value", sent_detections[0])

    def test_process_v2_github_push_no_enabled_discord_webhook_does_not_crash(self):
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
                return_value=[{"id": "detection-1"}],
            ),
            patch(
                "app.services.v2_webhook_processor.list_enabled_discord_webhooks_for_workspace",
                return_value=[],
            ),
            patch(
                "app.services.v2_webhook_processor.send_detection_alert"
            ) as send_alert,
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

        send_alert.assert_not_called()
        update_status.assert_called_with(
            scan_event_id="scan-event-1",
            status="completed",
            completed_at=ANY,
        )

    def test_process_v2_github_push_discord_failure_keeps_scan_completed(self):
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
                return_value=[{"id": "detection-1"}],
            ),
            patch(
                "app.services.v2_webhook_processor.list_enabled_discord_webhooks_for_workspace",
                return_value=[
                    {
                        "id": "webhook-1",
                        "workspace_id": "workspace-1",
                        "webhook_url_ciphertext": "ciphertext",
                    }
                ],
            ),
            patch(
                "app.services.v2_webhook_processor.decrypt_webhook_url",
                return_value="https://discord.com/api/webhooks/secret",
            ),
            patch(
                "app.services.v2_webhook_processor.send_detection_alert",
                side_effect=DiscordWebhookServiceError("network failed"),
            ),
            patch(
                "app.services.v2_webhook_processor.update_discord_webhook_alert_status"
            ) as update_alert_status,
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

        update_alert_status.assert_called_with(
            workspace_id="workspace-1",
            webhook_id="webhook-1",
            last_error="DiscordWebhookServiceError",
        )
        update_status.assert_called_with(
            scan_event_id="scan-event-1",
            status="completed",
            completed_at=ANY,
        )

    def test_send_detection_alert_uses_masked_value_only(self):
        response = Mock()
        response.raise_for_status.return_value = None

        with patch(
            "app.services.discord_webhook_service.requests.post",
            return_value=response,
        ) as post:
            send_detection_alert(
                "https://discord.com/api/webhooks/secret",
                {
                    "repo_full_name": "owner/repo",
                    "severity": "high",
                    "secret_type": "api_key",
                    "masked_value": "sk_l***************cdef",
                    "raw_value": "sk_live_123456789abcdef",
                    "webhook_url_ciphertext": "ciphertext",
                    "file_path": "config.py",
                    "line_number": 1,
                    "commit_sha": "abc123",
                    "status": "open",
                },
            )

        payload = post.call_args.kwargs["json"]
        self.assertIn("sk_l***************cdef", str(payload))
        self.assertNotIn("sk_live_123456789abcdef", str(payload))
        self.assertNotIn("ciphertext", str(payload))

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
