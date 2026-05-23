import hashlib
import hmac
import asyncio
import json
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks

from app.config import settings
from app.routes.webhook import github_webhook


class FakeRequest:
    def __init__(self, body: bytes, headers: dict, payload: dict):
        self._body = body
        self.headers = headers
        self._payload = payload

    async def body(self):
        return self._body

    async def json(self):
        return self._payload


class WebhookV2RoutingTests(unittest.TestCase):
    def setUp(self):
        self.previous_secret = settings.github_webhook_secret
        settings.github_webhook_secret = "test-secret"

    def tearDown(self):
        settings.github_webhook_secret = self.previous_secret

    def _run_signed_push(self, payload: dict):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        digest = hmac.new(
            settings.github_webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        request = FakeRequest(
            body=body,
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-GitHub-Delivery": "delivery-123",
                "X-Hub-Signature-256": f"sha256={digest}",
            },
        )
        background_tasks = BackgroundTasks()

        response = asyncio.run(github_webhook(request, background_tasks))
        return response, background_tasks

    def _push_payload(self):
        return {
            "ref": "refs/heads/main",
            "installation": {"id": 12345},
            "repository": {
                "id": 98765,
                "full_name": "owner/repo",
                "name": "repo",
                "owner": {"login": "owner"},
            },
            "pusher": {"name": "dev", "email": "dev@example.com"},
            "head_commit": {"id": "abc123"},
            "commits": [{"id": "abc123", "message": "test"}],
        }

    def test_v2_monitored_repository_creates_scan_event_without_queueing_v1_processor(self):
        with (
            patch(
                "app.routes.webhook.find_repository_by_installation_and_repo_id",
                return_value={
                    "workspace_id": "workspace-1",
                    "repository_id": "repository-1",
                    "full_name": "owner/repo",
                    "monitoring_enabled": True,
                    "github_installation_id": 12345,
                },
            ),
            patch("app.routes.webhook.find_scan_event_by_delivery", return_value=None),
            patch(
                "app.routes.webhook.create_scan_event",
                return_value={"id": "scan-event-1", "status": "running"},
            ) as create_scan_event,
            patch("app.routes.webhook.process_v2_github_push"),
            patch("app.routes.webhook.process_github_push") as process_github_push,
        ):
            response, background_tasks = self._run_signed_push(self._push_payload())

        self.assertEqual(response["status"], "queued")
        self.assertTrue(response["v2_repository_matched"])
        self.assertTrue(response["monitoring_enabled"])
        self.assertEqual(response["scan_event_id"], "scan-event-1")
        self.assertEqual(len(background_tasks.tasks), 1)
        create_scan_event.assert_called_once()
        process_github_push.assert_not_called()

    def test_v2_disabled_repository_skips_without_queueing_v1_processor(self):
        with (
            patch(
                "app.routes.webhook.find_repository_by_installation_and_repo_id",
                return_value={
                    "workspace_id": "workspace-1",
                    "repository_id": "repository-1",
                    "full_name": "owner/repo",
                    "monitoring_enabled": False,
                    "github_installation_id": 12345,
                },
            ),
            patch("app.routes.webhook.process_github_push") as process_github_push,
        ):
            response, background_tasks = self._run_signed_push(self._push_payload())

        self.assertEqual(response["status"], "skipped")
        self.assertTrue(response["v2_repository_matched"])
        self.assertFalse(response["monitoring_enabled"])
        self.assertEqual(len(background_tasks.tasks), 0)
        process_github_push.assert_not_called()

    def test_unknown_v2_repository_preserves_existing_v1_queue_behavior(self):
        with (
            patch(
                "app.routes.webhook.find_repository_by_installation_and_repo_id",
                return_value=None,
            ),
            patch("app.routes.webhook.process_github_push") as process_github_push,
        ):
            response, background_tasks = self._run_signed_push(self._push_payload())

        self.assertEqual(response["status"], "queued")
        self.assertFalse(response["v2_repository_matched"])
        self.assertEqual(len(background_tasks.tasks), 1)
        process_github_push.assert_not_called()

    def test_duplicate_v2_delivery_skips_without_queueing_processors(self):
        with (
            patch(
                "app.routes.webhook.find_repository_by_installation_and_repo_id",
                return_value={
                    "workspace_id": "workspace-1",
                    "repository_id": "repository-1",
                    "full_name": "owner/repo",
                    "monitoring_enabled": True,
                    "github_installation_id": 12345,
                },
            ),
            patch(
                "app.routes.webhook.find_scan_event_by_delivery",
                return_value={"id": "scan-event-1", "status": "completed"},
            ),
            patch("app.routes.webhook.create_scan_event") as create_scan_event,
            patch("app.routes.webhook.process_v2_github_push"),
            patch("app.routes.webhook.process_github_push") as process_github_push,
        ):
            response, background_tasks = self._run_signed_push(self._push_payload())

        self.assertEqual(response["status"], "duplicate")
        self.assertEqual(response["scan_event_id"], "scan-event-1")
        self.assertEqual(response["scan_event_status"], "completed")
        self.assertEqual(len(background_tasks.tasks), 0)
        create_scan_event.assert_not_called()
        process_github_push.assert_not_called()


if __name__ == "__main__":
    unittest.main()
