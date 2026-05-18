def parse_push_payload(payload: dict) -> dict:
    """Extract the GitHub push fields we need for later phases."""
    repository = payload.get("repository") or {}
    owner = repository.get("owner") or {}
    pusher = payload.get("pusher") or {}
    commits = payload.get("commits") or []
    head_commit = payload.get("head_commit") or {}

    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "") if ref else "unknown"

    commit_shas = []
    commit_messages = []
    added_files = []
    modified_files = []
    removed_files = []

    for commit in commits:
        commit_shas.append(commit.get("id", "unknown"))
        commit_messages.append(commit.get("message", "unknown"))
        added_files.extend(commit.get("added") or [])
        modified_files.extend(commit.get("modified") or [])
        removed_files.extend(commit.get("removed") or [])

    return {
        "repo_full_name": repository.get("full_name", "unknown"),
        "repo_owner": owner.get("login", "unknown"),
        "repo_name": repository.get("name", "unknown"),
        "branch": branch,
        "pusher_name": pusher.get("name", "unknown"),
        "pusher_email": pusher.get("email", "unknown"),
        "head_commit_sha": head_commit.get("id", "unknown"),
        "commit_count": len(commits),
        "commit_shas": commit_shas,
        "commit_messages": commit_messages,
        "added_files": added_files,
        "modified_files": modified_files,
        "removed_files": removed_files,
    }
