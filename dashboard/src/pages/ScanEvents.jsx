import React, { useEffect, useState } from "react";

import AppShell from "../components/AppShell.jsx";
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
    <AppShell
      title="Scan events"
      description="Recent V2 GitHub App scan activity."
      actions={
        <button className="button button-secondary" onClick={() => loadScanEvents()}>
          Refresh
        </button>
      }
    >

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
        <div className="empty-state">No V2 scan events found.</div>
      ) : (
        <section className="panel">
          <div className="section-heading">
            <h2>Scan history</h2>
            <span className="muted">{scanEvents.length} events</span>
          </div>
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
                    <td className="strong-cell">{scanEvent.repo_full_name || "-"}</td>
                    <td className="mono">{scanEvent.branch || "-"}</td>
                    <td className="mono">{shortSha(scanEvent.commit_sha)}</td>
                    <td>
                      <span className={`badge badge-${scanEvent.status || "muted"}`}>
                        {scanEvent.status || "unknown"}
                      </span>
                    </td>
                    <td className={scanEvent.error_message ? "error-text" : ""}>
                      {scanEvent.error_message || "-"}
                    </td>
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
    </AppShell>
  );
}

export default ScanEvents;
