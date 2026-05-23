import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  getRepositories,
  updateRepositoryMonitoring,
} from "../services/api.js";

function Repositories() {
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState("");

  async function loadRepositories() {
    setLoading(true);
    setError("");

    try {
      const data = await getRepositories();
      setRepositories(Array.isArray(data) ? data : []);
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Repositories could not be loaded. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRepositories();
  }, []);

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

  return (
    <main className="dashboard">
      <header className="hero">
        <div>
          <h1>Repositories</h1>
          <p>Manage monitoring status for synced GitHub repositories</p>
        </div>
        <div className="header-actions">
          <Link className="refresh-button" to="/dashboard">
            Dashboard
          </Link>
          <button className="refresh-button" onClick={loadRepositories}>
            Refresh
          </button>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      {loading ? (
        <div className="loading-state">Loading repositories...</div>
      ) : repositories.length === 0 ? (
        <div className="loading-state">
          No repositories found. Sync repositories from a GitHub installation
          first.
        </div>
      ) : (
        <section className="panel">
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
                  <td>{repository.full_name}</td>
                  <td>{repository.private ? "Private" : "Public"}</td>
                  <td>{repository.default_branch || "-"}</td>
                  <td>
                    <button
                      type="button"
                      className="status-button"
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
        </section>
      )}
    </main>
  );
}

export default Repositories;
