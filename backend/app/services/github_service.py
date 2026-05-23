import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings


HUNK_HEADER_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def fetch_commit_diff(repo_full_name: str, commit_sha: str) -> dict:
    """Fetch commit details from GitHub and return changed file data."""
    # TODO(V2): Use a GitHub App installation token for the repository owner
    # instead of the V1 global GITHUB_TOKEN.
    if not settings.github_token:
        raise ValueError("GITHUB_TOKEN is not configured")

    url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.github_token}",
        "User-Agent": "AI-SecureWatch",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
            commit_data = json.loads(response_body)
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"GitHub API error status: {exc.code}")
        print(f"GitHub API error response: {error_body}")
        return {"commit_sha": commit_sha, "files": []}
    except URLError as exc:
        print(f"GitHub API request failed: {exc.reason}")
        return {"commit_sha": commit_sha, "files": []}
    except Exception as exc:
        print(f"Unexpected GitHub API error: {exc}")
        return {"commit_sha": commit_sha, "files": []}

    changed_files = []

    for file_data in commit_data.get("files", []):
        changed_files.append(
            {
                "filename": file_data.get("filename", "unknown"),
                "status": file_data.get("status", "unknown"),
                "additions": file_data.get("additions", 0),
                "deletions": file_data.get("deletions", 0),
                "changes": file_data.get("changes", 0),
                "patch": file_data.get("patch", ""),
            }
        )

    return {
        "commit_sha": commit_sha,
        "files": changed_files,
    }


def fetch_commit_diff_with_token(
    repo_full_name: str, commit_sha: str, access_token: str
) -> dict:
    """Fetch commit details using a GitHub App installation access token."""
    if not access_token:
        raise ValueError("GitHub installation access token is missing")

    url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "AI-SecureWatch",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
            commit_data = json.loads(response_body)
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"GitHub App API error status: {exc.code}")
        print(f"GitHub App API error response: {error_body}")
        return {"commit_sha": commit_sha, "files": []}
    except URLError as exc:
        print(f"GitHub App API request failed: {exc.reason}")
        return {"commit_sha": commit_sha, "files": []}
    except Exception as exc:
        print(f"Unexpected GitHub App API error: {exc}")
        return {"commit_sha": commit_sha, "files": []}

    changed_files = []

    for file_data in commit_data.get("files", []):
        changed_files.append(
            {
                "filename": file_data.get("filename", "unknown"),
                "status": file_data.get("status", "unknown"),
                "additions": file_data.get("additions", 0),
                "deletions": file_data.get("deletions", 0),
                "changes": file_data.get("changes", 0),
                "patch": file_data.get("patch", ""),
            }
        )

    return {
        "commit_sha": commit_sha,
        "files": changed_files,
    }


def extract_added_lines(files: list) -> list:
    """Extract newly added lines from GitHub patch text with new-file line numbers."""
    added_lines = []

    for file_data in files:
        file_path = file_data.get("filename", "unknown")
        patch = file_data.get("patch", "")
        current_new_line_number = None

        for line in patch.splitlines():
            hunk_match = HUNK_HEADER_PATTERN.match(line)
            if hunk_match:
                current_new_line_number = int(hunk_match.group(1))
                continue

            if line.startswith("\\"):
                continue

            if line.startswith("+++") or line.startswith("---"):
                continue

            if line.startswith("+"):
                added_lines.append(
                    {
                        "file_path": file_path,
                        "line_content": line[1:],
                        "line_number": current_new_line_number,
                    }
                )
                if current_new_line_number is not None:
                    current_new_line_number += 1
                continue

            if line.startswith("-"):
                continue

            if current_new_line_number is not None:
                current_new_line_number += 1

    return added_lines
