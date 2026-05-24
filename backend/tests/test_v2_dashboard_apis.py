import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.dependencies.auth import CurrentUser
from app.routes.v2_dashboard import v2_detections, v2_scan_events
from app.services.database_service import (
    get_v2_dashboard_overview,
    list_v2_detections,
    update_v2_detection_status,
)


class V2DashboardApiServiceTests(unittest.TestCase):
    def test_overview_is_scoped_to_user_workspace(self):
        def fake_table_request(table_name, method, query_params=None, payload=None, **_):
            self.assertEqual(method, "GET")
            self.assertEqual(query_params["workspace_id"], "eq.workspace-1")
            if table_name == "repositories":
                return [
                    {"id": "repo-1", "monitoring_enabled": True},
                    {"id": "repo-2", "monitoring_enabled": False},
                ]
            if table_name == "scan_events":
                return [
                    {"id": "scan-1", "status": "completed", "created_at": "2026-01-02"},
                    {"id": "scan-2", "status": "failed", "created_at": "2026-01-01"},
                ]
            if table_name == "v2_detections":
                return [
                    {"id": "det-1", "status": "open", "severity": "critical"},
                    {"id": "det-2", "status": "resolved", "severity": "high"},
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
            overview = get_v2_dashboard_overview("user-1")

        self.assertEqual(overview["total_repositories"], 2)
        self.assertEqual(overview["monitored_repositories"], 1)
        self.assertEqual(overview["completed_scan_events"], 1)
        self.assertEqual(overview["failed_scan_events"], 1)
        self.assertEqual(overview["critical_detections"], 1)
        self.assertEqual(overview["high_detections"], 1)

    def test_list_v2_detections_returns_safe_fields_only(self):
        with (
            patch(
                "app.services.database_service.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.services.database_service._send_supabase_table_request",
                return_value=[
                    {
                        "id": "det-1",
                        "repository_id": "repo-1",
                        "scan_event_id": "scan-1",
                        "repo_full_name": "owner/repo",
                        "masked_value": "sk_l***************cdef",
                        "raw_value": "sk_live_123456789abcdef",
                        "raw_secret": "sk_live_123456789abcdef",
                        "secret_value": "sk_live_123456789abcdef",
                    }
                ],
            ),
        ):
            detections = list_v2_detections("user-1", {"limit": 50})

        self.assertEqual(detections[0]["masked_value"], "sk_l***************cdef")
        self.assertNotIn("raw_value", detections[0])
        self.assertNotIn("raw_secret", detections[0])
        self.assertNotIn("secret_value", detections[0])

    def test_update_v2_detection_status_rejects_other_workspace_detection(self):
        with (
            patch(
                "app.services.database_service.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.services.database_service._send_supabase_table_request",
                return_value=[],
            ) as table_request,
        ):
            updated = update_v2_detection_status("user-1", "det-1", "resolved")

        self.assertIsNone(updated)
        table_request.assert_called_once()

    def test_invalid_scan_event_status_filter_returns_400(self):
        with self.assertRaises(HTTPException) as context:
            v2_scan_events(
                status="not-a-status",
                current_user=CurrentUser(id="user-1"),
            )

        self.assertEqual(context.exception.status_code, 400)

    def test_invalid_detection_severity_filter_returns_400(self):
        with self.assertRaises(HTTPException) as context:
            v2_detections(
                severity="urgent",
                current_user=CurrentUser(id="user-1"),
            )

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
