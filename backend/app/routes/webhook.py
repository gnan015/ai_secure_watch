from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.config import settings
from app.services.database_service import (
    DatabaseError,
    create_scan_event,
    find_repository_by_installation_and_repo_id,
    find_scan_event_by_delivery,
)
from app.services.v2_webhook_processor import process_v2_github_push
from app.services.webhook_processor import process_github_push
from app.utils.github_payload import parse_push_payload
from app.utils.signature import verify_github_signature

router = APIRouter()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    github_event = request.headers.get("X-GitHub-Event", "unknown")
    github_delivery = request.headers.get("X-GitHub-Delivery", "unknown")
    github_signature = request.headers.get("X-Hub-Signature-256", "")
    payload_body = await request.body()

    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="GitHub webhook secret is not configured",
        )

    is_valid_signature = verify_github_signature(
        payload_body=payload_body,
        signature_header=github_signature,
        secret=settings.github_webhook_secret,
    )

    if not is_valid_signature:
        raise HTTPException(
            status_code=401,
            detail="Invalid GitHub webhook signature",
        )

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    repository_payload = payload.get("repository") or {}
    installation_payload = payload.get("installation") or {}
    installation_id = installation_payload.get("id")
    github_repo_id = repository_payload.get("id")
    repo_full_name = repository_payload.get("full_name", "unknown")

    webhook_context = {
        "delivery_id": github_delivery,
        "event_type": github_event,
        "installation_id": installation_id,
        "github_repo_id": github_repo_id,
        "repo_full_name": repo_full_name,
        "v2_repository_matched": False,
        "monitoring_enabled": None,
    }

    if github_event != "push":
        print(f"GitHub event ignored: {webhook_context}")
        return {
            "status": "ignored",
            "reason": "Only push events are supported for now",
            **webhook_context,
        }

    if installation_id is not None and github_repo_id is not None:
        try:
            v2_repository = find_repository_by_installation_and_repo_id(
                installation_id=int(installation_id),
                github_repo_id=int(github_repo_id),
            )
        except (TypeError, ValueError):
            v2_repository = None
        except DatabaseError as exc:
            print(f"V2 webhook repository lookup failed safely: {type(exc).__name__}")
            v2_repository = None

        if v2_repository:
            webhook_context["v2_repository_matched"] = True
            webhook_context["monitoring_enabled"] = v2_repository[
                "monitoring_enabled"
            ]

            if not v2_repository["monitoring_enabled"]:
                print(f"V2 GitHub App push skipped: {webhook_context}")
                print(f"V2 repository context: {v2_repository}")
                return {
                    "status": "skipped",
                    "reason": "Repository monitoring is disabled",
                    **webhook_context,
                }

            existing_scan_event = find_scan_event_by_delivery(
                workspace_id=v2_repository["workspace_id"],
                repository_id=v2_repository["repository_id"],
                github_delivery_id=github_delivery,
            )
            if existing_scan_event and existing_scan_event.get("status") in {
                "running",
                "completed",
            }:
                print(f"V2 duplicate GitHub App delivery skipped: {webhook_context}")
                print(f"V2 repository context: {v2_repository}")
                return {
                    "status": "duplicate",
                    "message": "V2 scan event already exists for this delivery",
                    "scan_event_id": existing_scan_event.get("id"),
                    "scan_event_status": existing_scan_event.get("status"),
                    **webhook_context,
                }

            push_data = parse_push_payload(payload)
            scan_event = create_scan_event(
                {
                    "workspace_id": v2_repository["workspace_id"],
                    "repository_id": v2_repository["repository_id"],
                    "github_delivery_id": github_delivery,
                    "event_type": github_event,
                    "repo_full_name": push_data["repo_full_name"],
                    "branch": push_data["branch"],
                    "commit_sha": push_data["head_commit_sha"],
                    "status": "running",
                    "started_at": _utc_now(),
                }
            )
            background_tasks.add_task(
                process_v2_github_push,
                scan_event,
                push_data,
                v2_repository,
            )

            print(f"V2 GitHub App push scan queued: {webhook_context}")
            print(f"V2 repository context: {v2_repository}")
            return {
                "status": "queued",
                "message": "V2 scan event queued",
                "scan_event_id": scan_event.get("id"),
                "scan_event_status": scan_event.get("status"),
                **webhook_context,
            }

    push_data = parse_push_payload(payload)

    # Queue longer work so GitHub gets a fast response from this webhook.
    background_tasks.add_task(process_github_push, push_data, payload)

    print("GitHub push event queued for background processing")
    print(f"Event type: {github_event}")
    print(f"Delivery ID: {github_delivery}")
    print(f"Repository: {push_data['repo_full_name']}")
    print(f"Branch: {push_data['branch']}")
    print(f"Head commit SHA: {push_data['head_commit_sha']}")
    print(f"Webhook context: {webhook_context}")

    return {
        "status": "queued",
        "event": "push",
        "message": "GitHub push event queued for background processing",
        **webhook_context,
        "data": {
            "repo_full_name": push_data["repo_full_name"],
            "branch": push_data["branch"],
            "head_commit_sha": push_data["head_commit_sha"],
            "commit_count": push_data["commit_count"],
        },
    }
