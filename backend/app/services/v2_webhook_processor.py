import logging
from datetime import datetime, timezone

from app.services.ai_service import analyze_secret_with_ai
from app.services.database_service import (
    DatabaseError,
    create_v2_detections_bulk,
    list_enabled_discord_webhooks_for_workspace,
    should_store_detection,
    update_discord_webhook_alert_status,
    update_scan_event_status,
)
from app.services.discord_webhook_service import (
    DiscordWebhookServiceError,
    decrypt_webhook_url,
    send_detection_alert,
)
from app.services.github_app_service import get_installation_access_token
from app.services.github_service import extract_added_lines, fetch_commit_diff_with_token
from app.services.scanner_service import scan_added_lines
from app.utils.safe_logging import log_safe


SEVERITY_MAP = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _v2_severity(ai_analysis: dict) -> str:
    risk_level = str(ai_analysis.get("risk_level", "MEDIUM")).upper()
    return SEVERITY_MAP.get(risk_level, "medium")


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, DatabaseError):
        return f"{type(exc).__name__}: {str(exc)[:200]}"
    return type(exc).__name__


def _stored_alert_detections(
    stored_detections: list[dict], detections_to_store: list[dict]
) -> list[dict]:
    alert_detections: list[dict] = []
    for index, detection in enumerate(detections_to_store):
        stored = stored_detections[index] if index < len(stored_detections) else {}
        alert_detections.append({**detection, **stored})
    return alert_detections


def _send_v2_discord_alerts(workspace_id: str, detections: list[dict]) -> None:
    if not detections:
        return

    try:
        webhooks = list_enabled_discord_webhooks_for_workspace(workspace_id)
    except DatabaseError as exc:
        log_safe(
            logging.ERROR,
            "v2_discord_webhook_lookup_failed",
            workspace_id=workspace_id,
            error_type=type(exc).__name__,
            error_message=_safe_error_message(exc),
        )
        return

    if not webhooks:
        log_safe(
            logging.INFO,
            "v2_discord_no_enabled_webhook",
            workspace_id=workspace_id,
            detections_stored=len(detections),
        )
        return

    alerts_sent = 0
    alerts_failed = 0
    for webhook in webhooks:
        webhook_id = webhook.get("id")
        try:
            webhook_url = decrypt_webhook_url(webhook["webhook_url_ciphertext"])
            for detection in detections:
                send_detection_alert(webhook_url, detection)
                alerts_sent += 1
            try:
                update_discord_webhook_alert_status(
                    workspace_id=workspace_id,
                    webhook_id=webhook_id,
                    last_error=None,
                )
            except DatabaseError:
                pass
        except (DiscordWebhookServiceError, KeyError) as exc:
            alerts_failed += len(detections)
            error_message = _safe_error_message(exc)
            log_safe(
                logging.ERROR,
                "v2_discord_alert_failed",
                workspace_id=workspace_id,
                discord_webhook_id=webhook_id,
                alerts_failed=len(detections),
                error_type=type(exc).__name__,
                error_message=error_message,
            )
            if webhook_id:
                try:
                    update_discord_webhook_alert_status(
                        workspace_id=workspace_id,
                        webhook_id=webhook_id,
                        last_error=error_message,
                    )
                except DatabaseError:
                    pass

    log_safe(
        logging.INFO,
        "v2_discord_alerts_finished",
        workspace_id=workspace_id,
        alerts_sent=alerts_sent,
        alerts_failed=alerts_failed,
    )


def process_v2_github_push(
    scan_event: dict, parsed_data: dict, v2_repository: dict
) -> None:
    """Process a monitored V2 GitHub App push and store masked detections."""
    scan_event_id = scan_event["id"]
    repo_full_name = parsed_data.get("repo_full_name") or v2_repository.get("full_name")
    commit_shas = parsed_data.get("commit_shas", [])

    print("Starting V2 GitHub App push processing")
    print(f"Scan event: {scan_event_id}")
    print(f"Repository: {repo_full_name}")
    print(f"Commit SHAs: {commit_shas}")

    try:
        log_safe(
            logging.INFO,
            "v2_scan_started",
            scan_event_id=scan_event_id,
            repo_full_name=repo_full_name,
            workspace_id=v2_repository.get("workspace_id"),
            repository_id=v2_repository.get("repository_id"),
            status="running",
        )
        access_token_payload = get_installation_access_token(
            int(v2_repository["github_installation_id"])
        )
        access_token = access_token_payload.get("token")
        if not access_token:
            raise ValueError("GitHub installation access token is missing")

        detections_to_store: list[dict] = []
        detections_found = 0

        for commit_sha in commit_shas:
            diff_data = fetch_commit_diff_with_token(
                repo_full_name=repo_full_name,
                commit_sha=commit_sha,
                access_token=access_token,
            )
            changed_files = diff_data.get("files", [])
            added_lines = extract_added_lines(changed_files)
            detected_secrets = scan_added_lines(added_lines)
            detections_found += len(detected_secrets)

            print(f"V2 changed files found: {len(changed_files)}")
            print(f"V2 added lines extracted: {len(added_lines)}")
            print(f"V2 potential secrets found: {len(detected_secrets)}")

            for detected_secret in detected_secrets:
                ai_analysis = analyze_secret_with_ai(detected_secret)
                if not should_store_detection(ai_analysis):
                    continue

                detections_to_store.append(
                    {
                        "workspace_id": v2_repository["workspace_id"],
                        "repository_id": v2_repository["repository_id"],
                        "scan_event_id": scan_event_id,
                        "repo_full_name": repo_full_name,
                        "branch": parsed_data.get("branch", "unknown"),
                        "commit_sha": commit_sha,
                        "file_path": detected_secret.get("file_path", "unknown"),
                        "line_number": detected_secret.get("line_number"),
                        "secret_type": detected_secret.get("secret_type", "unknown"),
                        "masked_value": detected_secret.get("masked_value", ""),
                        "detection_method": detected_secret.get("detection_method"),
                        "entropy_score": detected_secret.get("entropy_score"),
                        "severity": _v2_severity(ai_analysis),
                        "confidence_score": ai_analysis.get("confidence_score", 0.5),
                        "ai_reasoning": ai_analysis.get("reason", ""),
                        "ai_recommendation": ai_analysis.get("recommendation", ""),
                        "status": "open",
                    }
                )

        log_safe(
            logging.INFO,
            "v2_scan_detections_found",
            scan_event_id=scan_event_id,
            repo_full_name=repo_full_name,
            workspace_id=v2_repository.get("workspace_id"),
            repository_id=v2_repository.get("repository_id"),
            detections_found=detections_found,
            detections_to_store=len(detections_to_store),
        )
        print(f"V2 detections_found count: {detections_found}")
        print(f"V2 detections eligible for storage: {len(detections_to_store)}")
        stored_detections = create_v2_detections_bulk(detections_to_store)
        if len(stored_detections) != len(detections_to_store):
            raise DatabaseError("V2 detection storage count mismatch")

        _send_v2_discord_alerts(
            workspace_id=v2_repository["workspace_id"],
            detections=_stored_alert_detections(stored_detections, detections_to_store),
        )

        update_scan_event_status(
            scan_event_id=scan_event_id,
            status="completed",
            completed_at=_utc_now(),
        )

        print("V2 GitHub App push processing completed")
        print(f"V2 detections_stored count: {len(stored_detections)}")
        log_safe(
            logging.INFO,
            "v2_scan_completed",
            scan_event_id=scan_event_id,
            repo_full_name=repo_full_name,
            workspace_id=v2_repository.get("workspace_id"),
            repository_id=v2_repository.get("repository_id"),
            detections_found=detections_found,
            detections_stored=len(stored_detections),
            status="completed",
        )
    except Exception as exc:
        error_message = _safe_error_message(exc)
        print(f"V2 GitHub App push processing failed: {error_message}")
        log_safe(
            logging.ERROR,
            "v2_scan_failed",
            scan_event_id=scan_event_id,
            repo_full_name=repo_full_name,
            workspace_id=v2_repository.get("workspace_id"),
            repository_id=v2_repository.get("repository_id"),
            error_type=type(exc).__name__,
            error_message=error_message,
            status="failed",
        )
        update_scan_event_status(
            scan_event_id=scan_event_id,
            status="failed",
            error_message=error_message,
            completed_at=_utc_now(),
        )
