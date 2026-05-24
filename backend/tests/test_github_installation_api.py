import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.dependencies.auth import CurrentUser
from app.routes.github_app import (
    InstallationSaveRequest,
    list_github_installations,
    save_github_installation,
    sync_installation_repositories,
)
from app.services.database_service import get_github_installations_for_user_workspace


class GitHubInstallationApiTests(unittest.TestCase):
    def test_list_installations_is_workspace_scoped_and_safe(self):
        def fake_table_request(table_name, method, query_params=None, **_):
            self.assertEqual(table_name, "github_installations")
            self.assertEqual(method, "GET")
            self.assertEqual(query_params["workspace_id"], "eq.workspace-1")
            self.assertNotIn("token", query_params["select"])
            self.assertNotIn("private_key", query_params["select"])
            return [
                {
                    "id": "installation-row-1",
                    "installation_id": 12345,
                    "account_login": "octocat",
                    "account_type": "User",
                    "app_slug": "ai-securewatch-scanner",
                    "created_at": "2026-05-24T00:00:00+00:00",
                    "updated_at": "2026-05-24T00:00:00+00:00",
                }
            ]

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
            rows = get_github_installations_for_user_workspace("user-1")

        self.assertEqual(rows[0]["account_login"], "octocat")
        self.assertNotIn("workspace_id", rows[0])
        self.assertNotIn("access_token", rows[0])
        self.assertNotIn("private_key", rows[0])

        with patch(
            "app.routes.github_app.get_github_installations_for_user_workspace",
            return_value=rows,
        ):
            response = list_github_installations(CurrentUser(id="user-1"))

        self.assertEqual(response, rows)

    def test_save_installation_uses_current_user_workspace(self):
        with (
            patch(
                "app.routes.github_app.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.routes.github_app.get_installation",
                return_value={
                    "id": 12345,
                    "account": {"login": "octocat", "type": "User", "id": 99},
                    "app_slug": "ai-securewatch-scanner",
                },
            ),
            patch(
                "app.routes.github_app.upsert_github_installation",
                return_value={
                    "workspace_id": "workspace-1",
                    "installation_id": 12345,
                    "account_login": "octocat",
                    "account_type": "User",
                    "account_id": 99,
                    "app_slug": "ai-securewatch-scanner",
                },
            ) as upsert,
        ):
            response = save_github_installation(
                InstallationSaveRequest(installation_id=12345),
                CurrentUser(id="user-1"),
            )

        upsert.assert_called_once()
        self.assertEqual(upsert.call_args.args[0]["workspace_id"], "workspace-1")
        self.assertEqual(upsert.call_args.args[0]["installed_by_user_id"], "user-1")
        self.assertEqual(response["installation_id"], 12345)
        self.assertNotIn("token", response)
        self.assertNotIn("private_key", response)

    def test_sync_installation_uses_saved_workspace_installation_and_returns_summaries(self):
        with (
            patch(
                "app.routes.github_app.get_owned_workspace_for_user",
                return_value={"id": "workspace-1"},
            ),
            patch(
                "app.routes.github_app.get_github_installation_for_workspace",
                return_value={"id": "installation-row-1", "installation_id": 12345},
            ),
            patch(
                "app.routes.github_app.list_installation_repositories",
                return_value=[
                    {
                        "id": 111,
                        "full_name": "octocat/repo",
                        "private": False,
                        "owner": {"login": "octocat"},
                        "name": "repo",
                    }
                ],
            ),
            patch(
                "app.routes.github_app.upsert_repositories_for_installation",
                return_value=[
                    {
                        "github_repo_id": 111,
                        "full_name": "octocat/repo",
                        "private": False,
                        "monitoring_enabled": True,
                    }
                ],
            ) as upsert_repositories,
        ):
            response = sync_installation_repositories(12345, CurrentUser(id="user-1"))

        upsert_repositories.assert_called_once()
        self.assertEqual(
            upsert_repositories.call_args.kwargs["github_installation_db_id"],
            "installation-row-1",
        )
        self.assertEqual(response["synced_count"], 1)
        self.assertEqual(response["repositories"][0]["full_name"], "octocat/repo")
        self.assertNotIn("token", response["repositories"][0])

    def test_sync_rejects_installation_not_saved_to_workspace(self):
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
