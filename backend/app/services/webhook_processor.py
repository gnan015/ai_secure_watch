from app.services.ai_service import analyze_secret_with_ai
from app.services.database_service import insert_detection, should_store_detection
from app.services.github_service import extract_added_lines, fetch_commit_diff
from app.services.scanner_service import scan_added_lines


def process_github_push(parsed_data: dict, original_payload: dict) -> None:
    """Background task placeholder for future GitHub push processing."""
    repo_full_name = parsed_data.get("repo_full_name", "unknown")
    commit_shas = parsed_data.get("commit_shas", [])

    print("Starting background processing for GitHub push")
    print(f"Repository: {repo_full_name}")
    print(f"Branch: {parsed_data.get('branch', 'unknown')}")
    print(f"Pusher name: {parsed_data.get('pusher_name', 'unknown')}")
    print(f"Pusher email: {parsed_data.get('pusher_email', 'unknown')}")
    print(f"Head commit: {parsed_data.get('head_commit_sha', 'unknown')}")
    print(f"Commit count: {parsed_data.get('commit_count', 0)}")
    print(f"Commit SHAs: {commit_shas}")
    print(f"Added files: {parsed_data.get('added_files', [])}")
    print(f"Modified files: {parsed_data.get('modified_files', [])}")
    print(f"Removed files: {parsed_data.get('removed_files', [])}")

    for commit_sha in commit_shas:
        print("Fetching commit diff from GitHub")
        print(f"Commit SHA: {commit_sha}")

        try:
            diff_data = fetch_commit_diff(repo_full_name, commit_sha)
        except ValueError as exc:
            print(f"GitHub diff fetch skipped: {exc}")
            continue

        changed_files = diff_data.get("files", [])
        added_lines = extract_added_lines(changed_files)

        print(f"Changed files found: {len(changed_files)}")
        print(f"Added lines extracted: {len(added_lines)}")

        print("Scanning added lines for secrets")
        detected_secrets = scan_added_lines(added_lines)

        for detected_secret in detected_secrets:
            ai_analysis = analyze_secret_with_ai(detected_secret)

            print("Potential secret detected")
            print(f"File: {detected_secret.get('file_path', 'unknown')}")
            print(f"Secret Type: {detected_secret.get('secret_type', 'unknown')}")
            print(f"Masked Value: {detected_secret.get('masked_value', '')}")
            print(
                f"Detection Method: {detected_secret.get('detection_method', 'regex')}"
            )
            if "entropy_score" in detected_secret:
                print(f"Entropy Score: {detected_secret.get('entropy_score')}")
            print("")
            print("AI Analysis:")
            print(f"Risk Level: {ai_analysis.get('risk_level', 'MEDIUM')}")
            print(f"Confidence: {ai_analysis.get('confidence_score', 0.5)}")
            print(f"Reason: {ai_analysis.get('reason', '')}")
            print(f"Recommendation: {ai_analysis.get('recommendation', '')}")

            if should_store_detection(ai_analysis):
                # Supabase stores detection records for later dashboard views.
                # Only masked secrets are included. raw_value is intentionally
                # left out of this database record.
                detection_record = {
                    "repo_full_name": repo_full_name,
                    "repo_owner": parsed_data.get("repo_owner", "unknown"),
                    "repo_name": parsed_data.get("repo_name", "unknown"),
                    "branch": parsed_data.get("branch", "unknown"),
                    "commit_sha": commit_sha,
                    "file_path": detected_secret.get("file_path", "unknown"),
                    "line_number": detected_secret.get("line_number"),
                    "secret_type": detected_secret.get("secret_type", "unknown"),
                    "masked_value": detected_secret.get("masked_value", ""),
                    "detection_method": detected_secret.get("detection_method"),
                    "entropy_score": detected_secret.get("entropy_score"),
                    "severity": ai_analysis.get("risk_level", "MEDIUM"),
                    "confidence_score": ai_analysis.get("confidence_score", 0.5),
                    "ai_reasoning": ai_analysis.get("reason", ""),
                    "ai_recommendation": ai_analysis.get("recommendation", ""),
                    "status": "open",
                    "pusher_name": parsed_data.get("pusher_name", "unknown"),
                    "pusher_email": parsed_data.get("pusher_email", "unknown"),
                }

                print("Storing risky detection in Supabase")
                stored_detection = insert_detection(detection_record)

                if stored_detection.get("stored") is False:
                    print("Detection storage failed")
                else:
                    print("Detection stored successfully")

                print(f"File: {detection_record['file_path']}")
                print(f"Secret Type: {detection_record['secret_type']}")
                print(f"Masked Value: {detection_record['masked_value']}")
                print(f"Severity: {detection_record['severity']}")
                print(f"Confidence: {detection_record['confidence_score']}")
            else:
                print("Detection ignored because AI marked it low risk")

    print("Background processing completed")
