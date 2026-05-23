import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  getV2Detections,
  updateV2DetectionStatus,
} from "../services/api.js";

const statusOptions = ["open", "ignored", "resolved", "false_positive"];

function formatTimestamp(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString();
}

function shortSha(value) {
  return value ? value.slice(0, 8) : "-";
}

function Detections() {
  const [detections, setDetections] = useState([]);
  const [filters, setFilters] = useState({ status: "", severity: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState("");

  async function loadDetections(nextFilters = filters) {
    setLoading(true);
    setError("");

    try {
      const params = { limit: 100 };
      if (nextFilters.status) params.status = nextFilters.status;
      if (nextFilters.severity) params.severity = nextFilters.severity;
      const data = await getV2Detections(params);
      setDetections(Array.isArray(data) ? data : []);
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "V2 detections could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDetections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterChange(key, value) {
    const nextFilters = { ...filters, [key]: value };
    setFilters(nextFilters);
    loadDetections(nextFilters);
  }

  async function handleStatusChange(detection, status) {
    if (updatingId || detection.status === status) {
      return;
    }

    setUpdatingId(detection.id);
    setError("");

    try {
      const updated = await updateV2DetectionStatus(detection.id, status);
      setDetections((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Detection status could not be updated."
      );
    } finally {
      setUpdatingId("");
    }
  }

  return (
    <main className="dashboard">
      <header className="hero">
        <div>
          <h1>Detections</h1>
          <p>Workspace-scoped V2 secret detections</p>
        </div>
        <div className="header-actions">
          <Link className="refresh-button" to="/dashboard">Dashboard</Link>
          <Link className="refresh-button" to="/scan-events">Scan Events</Link>
          <Link className="refresh-button" to="/repositories">Repositories</Link>
          <Link className="refresh-button" to="/integrations/discord">Discord</Link>
          <button className="refresh-button" onClick={() => loadDetections()}>
            Refresh
          </button>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="panel">
        <div className="filters">
          <label>
            Status
            <select
              value={filters.status}
              onChange={(event) => handleFilterChange("status", event.target.value)}
            >
              <option value="">All</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
          </label>
          <label>
            Severity
            <select
              value={filters.severity}
              onChange={(event) => handleFilterChange("severity", event.target.value)}
            >
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </label>
        </div>
      </section>

      {loading ? (
        <div className="loading-state">Loading V2 detections...</div>
      ) : detections.length === 0 ? (
        <div className="loading-state">No V2 detections found.</div>
      ) : (
        <section className="panel">
          <div className="table-shell">
            <table className="detection-table">
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Location</th>
                  <th>Secret</th>
                  <th>Severity</th>
                  <th>Confidence</th>
                  <th>Status</th>
                  <th>Detected</th>
                  <th>AI Notes</th>
                </tr>
              </thead>
              <tbody>
                {detections.map((detection) => {
                  const busy = updatingId === detection.id;
                  return (
                    <tr key={detection.id}>
                      <td>
                        <div>{detection.repo_full_name || "-"}</div>
                        <div className="muted mono">{shortSha(detection.commit_sha)}</div>
                      </td>
                      <td>
                        <div>{detection.file_path || "-"}</div>
                        <div className="muted">
                          {detection.line_number ? `Line ${detection.line_number}` : "-"}
                        </div>
                      </td>
                      <td>
                        <div>{detection.secret_type || "-"}</div>
                        <div className="masked-value">{detection.masked_value || "-"}</div>
                      </td>
                      <td>
                        <span className={`badge badge-${detection.severity || "muted"}`}>
                          {detection.severity || "unknown"}
                        </span>
                      </td>
                      <td>{detection.confidence_score ?? "-"}</td>
                      <td>
                        <select
                          className="status-select"
                          disabled={busy}
                          value={detection.status || "open"}
                          onChange={(event) =>
                            handleStatusChange(detection, event.target.value)
                          }
                        >
                          {statusOptions.map((status) => (
                            <option key={status} value={status}>{status}</option>
                          ))}
                        </select>
                      </td>
                      <td>{formatTimestamp(detection.detected_at)}</td>
                      <td className="long-text">
                        <div>{detection.ai_reasoning || "-"}</div>
                        {detection.ai_recommendation && (
                          <div className="muted">{detection.ai_recommendation}</div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}

export default Detections;
