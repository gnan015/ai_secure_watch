import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getV2ScanEvents } from "../services/api.js";

function formatTimestamp(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString();
}

function shortSha(value) {
  return value ? value.slice(0, 8) : "-";
}

function ScanEvents() {
  const [scanEvents, setScanEvents] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadScanEvents(nextStatus = status) {
    setLoading(true);
    setError("");

    try {
      const params = { limit: 50 };
      if (nextStatus) params.status = nextStatus;
      const data = await getV2ScanEvents(params);
      setScanEvents(Array.isArray(data) ? data : []);
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Scan events could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadScanEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleStatusChange(event) {
    const nextStatus = event.target.value;
    setStatus(nextStatus);
    loadScanEvents(nextStatus);
  }

  return (
    <main className="dashboard">
      <header className="hero">
        <div>
          <h1>Scan Events</h1>
          <p>Recent V2 GitHub App scan activity</p>
        </div>
        <div className="header-actions">
          <Link className="refresh-button" to="/dashboard">Dashboard</Link>
          <Link className="refresh-button" to="/detections">Detections</Link>
          <Link className="refresh-button" to="/repositories">Repositories</Link>
          <Link className="refresh-button" to="/integrations/discord">Discord</Link>
          <button className="refresh-button" onClick={() => loadScanEvents()}>
            Refresh
          </button>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="panel">
        <div className="filters">
          <label>
            Status
            <select value={status} onChange={handleStatusChange}>
              <option value="">All</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="skipped">Skipped</option>
            </select>
          </label>
        </div>
      </section>

      {loading ? (
        <div className="loading-state">Loading scan events...</div>
      ) : scanEvents.length === 0 ? (
        <div className="loading-state">No V2 scan events found.</div>
      ) : (
        <section className="panel">
          <div className="table-shell">
            <table className="detection-table">
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Branch</th>
                  <th>Commit</th>
                  <th>Status</th>
                  <th>Error</th>
                  <th>Started</th>
                  <th>Completed</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {scanEvents.map((scanEvent) => (
                  <tr key={scanEvent.id}>
                    <td>{scanEvent.repo_full_name || "-"}</td>
                    <td>{scanEvent.branch || "-"}</td>
                    <td className="mono">{shortSha(scanEvent.commit_sha)}</td>
                    <td>
                      <span className={`badge badge-${scanEvent.status || "muted"}`}>
                        {scanEvent.status || "unknown"}
                      </span>
                    </td>
                    <td>{scanEvent.error_message || "-"}</td>
                    <td>{formatTimestamp(scanEvent.started_at)}</td>
                    <td>{formatTimestamp(scanEvent.completed_at)}</td>
                    <td>{formatTimestamp(scanEvent.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}

export default ScanEvents;
