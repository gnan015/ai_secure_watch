import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.dependencies.auth import CurrentUser
from app.routes.discord_webhooks import (
    DiscordWebhookCreateRequest,
    DiscordWebhookUpdateRequest,
    create_discord_webhook,
    delete_discord_webhook,
    list_discord_webhooks,
    test_discord_webhook,
    update_discord_webhook,
)
from app.routes.github_app import sync_installation_repositories
from app.routes.repositories import RepositoryMonitoringUpdate, set_repository_monitoring
from app.routes.v2_dashboard import V2DetectionStatusUpdate, set_v2_detection_status
from app.services.database_service import (
    InvalidDetectionStatusError,
    get_repositories_for_user_workspace,
    list_v2_detections,
    list_v2_scan_events,
    update_repository_monitoring,
    update_v2_detection_status,
)


class Phase10LaunchSafetyTests(unittest.TestCase):
    sensitive_values = {
        "service-role-secret",
        "jwt-secret",
        "-----BEGIN PRIVATE KEY-----",
        "installation-token-secret",
        "https://discord.com/api/webhooks/raw-secret",
        "encrypted-discord-webhook-url",
        "sk_live_raw_secret_value",
        "Bearer user-access-token",
    }
    sensitive_keys = {
        "service_role_key",
        "supabase_service_role_key",
        "jwt_secret",
        "supabase_jwt_secret",
        "github_app_private_key",
        "installation_token",
        "authorization",
        "webhook_url",
        "webhook_url_ciphertext",
        "raw_value",
        "raw_secret",
        "secret_value",
    }

    def assert_no_sensitive_leak(self, payload):
        keys = set()

        def collect_keys(value):
            if isinstance(value, dict):
                keys.update(value.keys())
                for nested_value in value.values():
                    collect_keys(nested_value)
            elif isinstance(value, list):
                for item in value:
                    collect_keys(item)

        collect_keys(payload)
        serialized = json.dumps(payload, default=str)

        for key in self.sensitive_keys:
            self.assertNotIn(key, keys)
        for value in self.sensitive_values:
            self.assertNotIn(value, serialized)

    def test_v2_detection_status_update_is_workspace_scoped_and_safe(self):
        calls = []

        def fake_table_request(table_name, method, query_params=None, payload=None, **_):
            calls.append((table_name, method, query_params, payload))
            self.assertEqual(table_name, "v2_detections")
            self.assertEqual(query_params["workspace_id"], "eq.workspace-1")
            if method == "GET":
                return [{"id": "det-own"}]
            if method == "PATCH":
                return [
                    {
                        "id": "det-own",
                        "repository_id": "repo-1",
                        "scan_event_id": "scan-1",
                        "repo_full_name": "owner/repo",
                        "masked_value": "sk_l**************alue",
                        "status": "resolved",
                        "raw_value": "sk_live_raw_secret_value",
                        "installation_token": "installation-token-secret",
                    }
                ]
            return []

        with (
            patch(
                "app.services.database_service.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.services.database_service._send_supabase_table_request",
                side_effect=fake_table_request,
            ),
        ):
            updated = update_v2_detection_status("user-1", "det-own", "resolved")

        self.assertEqual(updated["status"], "resolved")
        self.assertEqual(len(calls), 2)
        self.assert_no_sensitive_leak(updated)

        with (
            patch(
                "app.routes.v2_dashboard.update_v2_detection_status",
                return_value={"id": "det-own", "status": "ignored"},
            ),
        ):
            response = set_v2_detection_status(
                "det-own",
                V2DetectionStatusUpdate(status="ignored"),
                CurrentUser(id="user-1"),
            )
        self.assertEqual(response["status"], "ignored")
        self.assert_no_sensitive_leak(response)

    def test_other_workspace_detection_update_fails_and_invalid_status_is_400(self):
        with patch(
            "app.routes.v2_dashboard.update_v2_detection_status",
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as context:
                set_v2_detection_status(
                    "det-other",
                    V2DetectionStatusUpdate(status="resolved"),
                    CurrentUser(id="user-1"),
                )
        self.assertEqual(context.exception.status_code, 404)

        with patch(
            "app.routes.v2_dashboard.update_v2_detection_status",
            side_effect=InvalidDetectionStatusError("invalid"),
        ):
            with self.assertRaises(HTTPException) as context:
                set_v2_detection_status(
                    "det-own",
                    V2DetectionStatusUpdate(status="not-valid"),
                    CurrentUser(id="user-1"),
                )
        self.assertEqual(context.exception.status_code, 400)

    def test_v2_detection_and_scan_event_lists_are_workspace_scoped_and_safe(self):
        def fake_table_request(table_name, method, query_params=None, **_):
            self.assertEqual(method, "GET")
            self.assertEqual(query_params["workspace_id"], "eq.workspace-1")
            if table_name == "v2_detections":
                return [
                    {
                        "id": "det-own",
                        "repository_id": "repo-1",
                        "scan_event_id": "scan-1",
                        "repo_full_name": "owner/repo",
                        "masked_value": "sk_l**************alue",
                        "raw_value": "sk_live_raw_secret_value",
                        "Authorization": "Bearer user-access-token",
                    }
                ]
            if table_name == "scan_events":
                return [
                    {
                        "id": "scan-1",
                        "repository_id": "repo-1",
                        "repo_full_name": "owner/repo",
                        "status": "completed",
                        "installation_token": "installation-token-secret",
                    }
                ]
            return []

        with (
            patch(
                "app.services.database_service.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.services.database_service._send_supabase_table_request",
                side_effect=fake_table_request,
            ),
        ):
            detections = list_v2_detections("user-1", {"limit": 50})
            scan_events = list_v2_scan_events("user-1", limit=20)

        self.assertEqual(detections[0]["id"], "det-own")
        self.assertEqual(scan_events[0]["id"], "scan-1")
        self.assert_no_sensitive_leak(detections)
        self.assert_no_sensitive_leak(scan_events)

    def test_repository_list_and_monitoring_update_are_workspace_scoped(self):
        select_values = []

        def fake_list_request(table_name, method, query_params=None, **_):
            self.assertEqual(table_name, "repositories")
            self.assertEqual(method, "GET")
            self.assertEqual(query_params["workspace_id"], "eq.workspace-1")
            select_values.append(query_params["select"])
            return [
                {
                    "id": "repo-1",
                    "github_repo_id": 123,
                    "full_name": "owner/repo",
                    "monitoring_enabled": True,
                }
            ]

        with (
            patch(
                "app.services.database_service.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.services.database_service._send_supabase_table_request",
                side_effect=fake_list_request,
            ),
        ):
            repositories = get_repositories_for_user_workspace("user-1")

        self.assertEqual(repositories[0]["id"], "repo-1")
        self.assertNotIn("webhook_url_ciphertext", select_values[0])
        self.assertNotIn("raw_value", select_values[0])
        self.assert_no_sensitive_leak(repositories)

        update_calls = []

        def fake_update_request(table_name, method, query_params=None, payload=None, **_):
            update_calls.append((method, query_params, payload))
            self.assertEqual(table_name, "repositories")
            self.assertEqual(query_params["workspace_id"], "eq.workspace-1")
            if method == "GET":
                return [{"id": "repo-1"}]
            if method == "PATCH":
                return [
                    {
                        "id": "repo-1",
                        "full_name": "owner/repo",
                        "monitoring_enabled": False,
                    }
                ]
            return []

        with (
            patch(
                "app.services.database_service.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.services.database_service._send_supabase_table_request",
                side_effect=fake_update_request,
            ),
        ):
            updated = update_repository_monitoring("user-1", "repo-1", False)

        self.assertFalse(updated["monitoring_enabled"])
        self.assertEqual(len(update_calls), 2)
        self.assert_no_sensitive_leak(updated)

        with patch(
            "app.routes.repositories.update_repository_monitoring",
            return_value={"id": "repo-1", "monitoring_enabled": True},
        ):
            response = set_repository_monitoring(
                "repo-1",
                RepositoryMonitoringUpdate(monitoring_enabled=True),
                CurrentUser(id="user-1"),
            )
        self.assertTrue(response["monitoring_enabled"])
        self.assert_no_sensitive_leak(response)

    def test_other_workspace_repository_update_fails(self):
        with patch(
            "app.routes.repositories.update_repository_monitoring",
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as context:
                set_repository_monitoring(
                    "repo-other",
                    RepositoryMonitoringUpdate(monitoring_enabled=False),
                    CurrentUser(id="user-1"),
                )
        self.assertEqual(context.exception.status_code, 404)

    def test_discord_webhook_actions_are_workspace_scoped_and_never_return_raw_url(self):
        safe_webhook = {
            "id": "webhook-1",
            "workspace_id": "workspace-1",
            "name": "Alerts",
            "webhook_url_last4": "cret",
            "enabled": True,
        }

        with patch(
            "app.routes.discord_webhooks.get_discord_webhooks_for_user_workspace",
            return_value=[safe_webhook],
        ):
            listed = list_discord_webhooks(CurrentUser(id="user-1"))
        self.assert_no_sensitive_leak(listed)

        with (
            patch(
                "app.routes.discord_webhooks.encrypt_webhook_url",
                return_value="encrypted-discord-webhook-url",
            ),
            patch("app.routes.discord_webhooks.mask_webhook_last4", return_value="cret"),
            patch(
                "app.routes.discord_webhooks.create_discord_webhook_for_user_workspace",
                return_value=safe_webhook,
            ),
        ):
            created = create_discord_webhook(
                DiscordWebhookCreateRequest(
                    name="Alerts",
                    webhook_url="https://discord.com/api/webhooks/raw-secret",
                    enabled=True,
                ),
                CurrentUser(id="user-1"),
            )
        self.assert_no_sensitive_leak(created)

        with (
            patch(
                "app.routes.discord_webhooks.encrypt_webhook_url",
                return_value="encrypted-discord-webhook-url",
            ),
            patch("app.routes.discord_webhooks.mask_webhook_last4", return_value="cret"),
            patch(
                "app.routes.discord_webhooks.update_discord_webhook_for_user_workspace",
                return_value={**safe_webhook, "enabled": False},
            ),
        ):
            updated = update_discord_webhook(
                "webhook-1",
                DiscordWebhookUpdateRequest(
                    webhook_url="https://discord.com/api/webhooks/raw-secret",
                    enabled=False,
                ),
                CurrentUser(id="user-1"),
            )
        self.assertFalse(updated["enabled"])
        self.assert_no_sensitive_leak(updated)

        with patch(
            "app.routes.discord_webhooks.delete_discord_webhook_for_user_workspace",
            return_value=True,
        ):
            deleted = delete_discord_webhook("webhook-1", CurrentUser(id="user-1"))
        self.assertEqual(deleted["status"], "deleted")
        self.assert_no_sensitive_leak(deleted)

        with (
            patch(
                "app.routes.discord_webhooks.get_discord_webhook_for_user_workspace",
                return_value={**safe_webhook, "webhook_url_ciphertext": "ciphertext"},
            ),
            patch(
                "app.routes.discord_webhooks.decrypt_webhook_url",
                return_value="https://discord.com/api/webhooks/raw-secret",
            ),
            patch("app.routes.discord_webhooks.get_owned_workspace_for_user", return_value={"name": "Workspace"}),
            patch("app.routes.discord_webhooks.send_test_webhook_message"),
            patch(
                "app.routes.discord_webhooks.update_discord_webhook_for_user_workspace",
                return_value={"last_tested_at": "2026-05-24T00:00:00+00:00"},
            ),
        ):
            tested = test_discord_webhook("webhook-1", CurrentUser(id="user-1"))
        self.assertEqual(tested["status"], "sent")
        self.assert_no_sensitive_leak(tested)

    def test_other_workspace_discord_webhook_actions_fail(self):
        with patch(
            "app.routes.discord_webhooks.update_discord_webhook_for_user_workspace",
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as context:
                update_discord_webhook(
                    "webhook-other",
                    DiscordWebhookUpdateRequest(enabled=False),
                    CurrentUser(id="user-1"),
                )
        self.assertEqual(context.exception.status_code, 404)

        with patch(
            "app.routes.discord_webhooks.delete_discord_webhook_for_user_workspace",
            return_value=False,
        ):
            with self.assertRaises(HTTPException) as context:
                delete_discord_webhook("webhook-other", CurrentUser(id="user-1"))
        self.assertEqual(context.exception.status_code, 404)

        with patch(
            "app.routes.discord_webhooks.get_discord_webhook_for_user_workspace",
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as context:
                test_discord_webhook("webhook-other", CurrentUser(id="user-1"))
        self.assertEqual(context.exception.status_code, 404)

    def test_other_workspace_github_installation_sync_fails(self):
        with (
            patch(
                "app.routes.github_app.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.routes.github_app.get_github_installation_for_workspace",
                return_value=None,
            ),
            patch("app.routes.github_app.list_installation_repositories") as list_repos,
        ):
            with self.assertRaises(HTTPException) as context:
                sync_installation_repositories(12345, CurrentUser(id="user-1"))

        self.assertEqual(context.exception.status_code, 404)
        list_repos.assert_not_called()


if __name__ == "__main__":
    unittest.main()
