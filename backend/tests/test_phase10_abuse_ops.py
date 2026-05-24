import inspect
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.dependencies.auth import CurrentUser, get_current_user
from app.routes.discord_webhooks import test_discord_webhook
from app.routes.v2_dashboard import v2_detections, v2_scan_events
from app.services.github_app_service import list_installation_repositories


class Phase10AbuseOpsTests(unittest.TestCase):
    def test_v2_dashboard_limit_max_is_enforced(self):
        detections_limit = inspect.signature(v2_detections).parameters["limit"].default
        scan_events_limit = inspect.signature(v2_scan_events).parameters["limit"].default

        self.assertTrue(any(getattr(item, "le", None) == 100 for item in detections_limit.metadata))
        self.assertTrue(any(getattr(item, "le", None) == 100 for item in scan_events_limit.metadata))

    def test_invalid_v2_filters_return_400(self):
        with self.assertRaises(HTTPException) as detections_context:
            v2_detections(status="not-valid", current_user=CurrentUser(id="user-1"))
        with self.assertRaises(HTTPException) as scan_events_context:
            v2_scan_events(status="not-valid", current_user=CurrentUser(id="user-1"))

        self.assertEqual(detections_context.exception.status_code, 400)
        self.assertEqual(scan_events_context.exception.status_code, 400)

    def test_discord_test_endpoint_requires_auth(self):
        current_user_dependency = inspect.signature(test_discord_webhook).parameters[
            "current_user"
        ].default

        self.assertIs(current_user_dependency.dependency, get_current_user)

    def test_discord_test_rejects_disabled_webhook_without_sending(self):
        with (
            patch(
                "app.routes.discord_webhooks.get_discord_webhook_for_user_workspace",
                return_value={
                    "id": "webhook-1",
                    "enabled": False,
                    "webhook_url_ciphertext": "ciphertext",
                },
            ),
            patch("app.routes.discord_webhooks.send_test_webhook_message") as send_test,
        ):
            with self.assertRaises(HTTPException) as context:
                test_discord_webhook("webhook-1", CurrentUser(id="user-1"))

        self.assertEqual(context.exception.status_code, 400)
        send_test.assert_not_called()

    def test_repository_sync_paginates_until_github_returns_short_page(self):
        full_page = Mock()
        full_page.status_code = 200
        full_page.json.return_value = {
            "repositories": [{"id": repo_id} for repo_id in range(100)]
        }
        final_page = Mock()
        final_page.status_code = 200
        final_page.json.return_value = {"repositories": [{"id": 100}, {"id": 101}]}

        with (
            patch(
                "app.services.github_app_service.get_installation_access_token",
                return_value={"token": "installation-token"},
            ),
            patch(
                "app.services.github_app_service.requests.get",
                side_effect=[full_page, full_page, final_page],
            ) as get,
        ):
            repositories = list_installation_repositories(12345)

        self.assertEqual(len(repositories), 202)
        self.assertEqual(get.call_count, 3)


if __name__ == "__main__":
    unittest.main()
