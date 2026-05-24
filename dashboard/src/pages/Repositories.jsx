import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import AppShell from "../components/AppShell.jsx";
import {
  getGitHubInstallations,
  getRepositories,
  syncGitHubInstallationRepositories,
  updateRepositoryMonitoring,
} from "../services/api.js";

const githubAppInstallUrl = import.meta.env.VITE_GITHUB_APP_INSTALL_URL || "";

function Repositories() {
  const location = useLocation();
  const [installations, setInstallations] = useState([]);
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(location.state?.notice || "");
  const [updatingId, setUpdatingId] = useState("");
  const [syncing, setSyncing] = useState(false);

  async function loadRepositorySetup({ clearNotice = false } = {}) {
    setLoading(true);
    setError("");
    if (clearNotice) {
      setNotice("");
    }

    try {
      const [installationData, repositoryData] = await Promise.all([
        getGitHubInstallations(),
        getRepositories(),
      ]);
      setInstallations(Array.isArray(installationData) ? installationData : []);
      setRepositories(Array.isArray(repositoryData) ? repositoryData : []);
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Repository setup could not be loaded. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRepositorySetup();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleInstallClick() {
    setError("");
    if (!githubAppInstallUrl) {
      setError("GitHub App install URL is not configured.");
      return;
    }
    window.location.assign(githubAppInstallUrl);
  }

  async function handleSyncRepositories() {
    if (syncing || installations.length === 0) {
      return;
    }

    setSyncing(true);
    setError("");
    setNotice("");

    try {
      const results = await Promise.all(
        installations.map((installation) =>
          syncGitHubInstallationRepositories(installation.installation_id)
        )
      );
      const syncedCount = results.reduce(
        (total, result) => total + (result?.synced_count || 0),
        0
      );
      setNotice(`Synced ${syncedCount} repositories.`);
      await loadRepositorySetup();
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Repositories could not be synced from the GitHub App installation."
      );
    } finally {
      setSyncing(false);
    }
  }

  async function handleToggle(repository) {
    if (updatingId) {
      return;
    }

    setUpdatingId(repository.id);
    setError("");

    try {
      const updated = await updateRepositoryMonitoring(
        repository.id,
        !repository.monitoring_enabled
      );

      setRepositories((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Repository monitoring could not be updated."
      );
    } finally {
      setUpdatingId("");
    }
  }

  const hasInstallation = installations.length > 0;
  const primaryInstallation = installations[0];

  return (
    <AppShell
      title="Repositories"
      description="Connect the GitHub App, sync accessible repositories, and choose what to monitor."
      actions={
        <>
          <button className="button button-primary" onClick={handleInstallClick}>
            {hasInstallation ? "Manage GitHub App" : "Install GitHub App"}
          </button>
          {hasInstallation && (
            <button
              className="button button-secondary"
              disabled={syncing}
              onClick={handleSyncRepositories}
            >
              {syncing ? "Syncing..." : "Sync repositories"}
            </button>
          )}
          <button
            className="button button-secondary"
            onClick={() => loadRepositorySetup({ clearNotice: true })}
          >
            Refresh
          </button>
        </>
      }
    >
      {error && <div className="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}

      <section className="panel">
        <div className="section-heading">
          <h2>GitHub App connection</h2>
          <span className={hasInstallation ? "badge badge-completed" : "badge badge-muted"}>
            {hasInstallation ? "Connected" : "Not connected"}
          </span>
        </div>
        {hasInstallation ? (
          <p className="muted">
            Installation connected for{" "}
            <span className="strong-cell">{primaryInstallation.account_login}</span>
            {installations.length > 1 ? ` and ${installations.length - 1} more` : ""}.
            Repository sync only imports repositories available to the GitHub App
            installation.
          </p>
        ) : (
          <p className="muted">
            No GitHub App installation is saved for this workspace yet. Install
            the app on all repositories or selected repositories, then sync.
          </p>
        )}
      </section>

      {loading ? (
        <div className="loading-state">Loading repository setup...</div>
      ) : repositories.length === 0 ? (
        <div className="empty-state">
          No repositories synced yet. Install the GitHub App or click Sync
          repositories.
        </div>
      ) : (
        <section className="panel">
          <div className="section-heading">
            <h2>Synced repositories</h2>
            <span className="muted">{repositories.length} total</span>
          </div>
          <div className="table-shell">
            <table className="detection-table">
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Visibility</th>
                  <th>Default Branch</th>
                  <th>Monitoring</th>
                  <th>GitHub</th>
                </tr>
              </thead>
              <tbody>
                {repositories.map((repository) => (
                  <tr key={repository.id}>
                    <td className="strong-cell">{repository.full_name}</td>
                    <td>
                      <span className="badge badge-muted">
                        {repository.private ? "Private" : "Public"}
                      </span>
                    </td>
                    <td className="mono">{repository.default_branch || "-"}</td>
                    <td>
                      <button
                        type="button"
                        className={
                          repository.monitoring_enabled
                            ? "toggle-button enabled"
                            : "toggle-button"
                        }
                        disabled={updatingId === repository.id}
                        onClick={() => handleToggle(repository)}
                      >
                        {updatingId === repository.id
                          ? "Updating..."
                          : repository.monitoring_enabled
                          ? "ON"
                          : "OFF"}
                      </button>
                    </td>
                    <td>
                      <a
                        className="inline-link"
                        href={repository.html_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </AppShell>
  );
}

export default Repositories;
