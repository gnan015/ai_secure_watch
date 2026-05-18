from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.config import settings
from app.services.webhook_processor import process_github_push
from app.utils.github_payload import parse_push_payload
from app.utils.signature import verify_github_signature

router = APIRouter()


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

    if github_event != "push":
        print(f"GitHub event ignored: {github_event}")
        return {
            "status": "ignored",
            "reason": "Only push events are supported for now",
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

    return {
        "status": "queued",
        "event": "push",
        "message": "GitHub push event queued for background processing",
        "data": {
            "repo_full_name": push_data["repo_full_name"],
            "branch": push_data["branch"],
            "head_commit_sha": push_data["head_commit_sha"],
            "commit_count": push_data["commit_count"],
        },
    }
