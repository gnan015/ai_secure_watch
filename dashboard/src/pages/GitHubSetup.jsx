import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import AppShell from "../components/AppShell.jsx";
import {
  saveGitHubInstallation,
  syncGitHubInstallationRepositories,
} from "../services/api.js";

function GitHubSetup() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("Connecting GitHub installation...");
  const [error, setError] = useState("");
  const [syncedCount, setSyncedCount] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function saveAndSyncInstallation() {
      const installationId = searchParams.get("installation_id");
      if (!installationId || Number.isNaN(Number(installationId))) {
        setError("GitHub setup did not include a valid installation_id.");
        setStatus("");
        return;
      }

      try {
        setStatus("Saving GitHub installation...");
        await saveGitHubInstallation(installationId);

        if (!isMounted) {
          return;
        }

        setStatus("Syncing available repositories...");
        const syncResult = await syncGitHubInstallationRepositories(installationId);

        if (!isMounted) {
          return;
        }

        setSyncedCount(syncResult?.synced_count ?? 0);
        setStatus("GitHub installation connected.");
        window.setTimeout(() => {
          if (isMounted) {
            navigate("/repositories", {
              replace: true,
              state: {
                notice: `Synced ${syncResult?.synced_count ?? 0} repositories.`,
              },
            });
          }
        }, 900);
      } catch (apiError) {
        if (!isMounted) {
          return;
        }
        setError(
          apiError?.response?.data?.detail ||
            "GitHub installation could not be saved or synced."
        );
        setStatus("");
      }
    }

    saveAndSyncInstallation();

    return () => {
      isMounted = false;
    };
  }, [navigate, searchParams]);

  return (
    <AppShell
      title="GitHub setup"
      description="Saving the GitHub App installation and syncing accessible repositories."
    >
      {error && <div className="alert">{error}</div>}
      {status && (
        <div className="panel">
          <div className="section-heading">
            <h2>{status}</h2>
          </div>
          <p className="muted">
            Keep this tab open while AI SecureWatch connects your installation.
          </p>
          {syncedCount !== null && (
            <div className="notice">Synced {syncedCount} repositories.</div>
          )}
        </div>
      )}
      {error && (
        <Link className="button button-secondary" to="/repositories">
          Back to repositories
        </Link>
      )}
    </AppShell>
  );
}

export default GitHubSetup;
