import React from "react";

import StatusBadge from "./StatusBadge.jsx";

function formatDate(value) {
  if (!value) return "unknown";
  return new Date(value).toLocaleString();
}

function DetectionTable({
  detections,
  filters,
  onFilterChange,
  onStatusChange,
  updatingId,
}) {
  return (
    <section className="panel full-table">
      <div className="section-heading">
        <h2>All Detections</h2>
      </div>

      <div className="filters">
        <label>
          Severity
          <select
            value={filters.severity}
            onChange={(event) => onFilterChange("severity", event.target.value)}
          >
            <option value="">All</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </label>

        <label>
          Status
          <select
            value={filters.status}
            onChange={(event) => onFilterChange("status", event.target.value)}
          >
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </label>

        <label>
          Repository
          <input
            value={filters.repo}
            onChange={(event) => onFilterChange("repo", event.target.value)}
            placeholder="owner/repo"
          />
        </label>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Repository</th>
              <th>Branch</th>
              <th>Commit</th>
              <th>File</th>
              <th>Line</th>
              <th>Type</th>
              <th>Masked Value</th>
              <th>Method</th>
              <th>Severity</th>
              <th>Confidence</th>
              <th>AI Reasoning</th>
              <th>Recommendation</th>
              <th>Status</th>
              <th>Pusher</th>
              <th>Detected</th>
            </tr>
          </thead>
          <tbody>
            {detections.map((detection) => (
              <tr key={detection.id}>
                <td>{detection.repo_full_name}</td>
                <td>{detection.branch}</td>
                <td className="mono">{detection.commit_sha}</td>
                <td>{detection.file_path}</td>
                <td>{detection.line_number ?? "unknown"}</td>
                <td>{detection.secret_type}</td>
                <td className="masked-value">{detection.masked_value}</td>
                <td>{detection.detection_method}</td>
                <td>
                  <StatusBadge value={detection.severity} type="severity" />
                </td>
                <td>{Math.round((detection.confidence_score || 0) * 100)}%</td>
                <td className="long-text">{detection.ai_reasoning}</td>
                <td className="long-text">{detection.ai_recommendation}</td>
                <td>
                  <select
                    className="status-select"
                    value={detection.status}
                    disabled={updatingId === detection.id}
                    onChange={(event) =>
                      onStatusChange(detection.id, event.target.value)
                    }
                  >
                    <option value="open">Open</option>
                    <option value="resolved">Resolved</option>
                    <option value="dismissed">Dismissed</option>
                  </select>
                </td>
                <td>
                  {detection.pusher_name}
                  <br />
                  <span className="muted">{detection.pusher_email}</span>
                </td>
                <td>{formatDate(detection.detected_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {detections.length === 0 && (
          <div className="empty-state">No detections match the current filters.</div>
        )}
      </div>
    </section>
  );
}

export default DetectionTable;
