import React from "react";

import StatusBadge from "./StatusBadge.jsx";

function formatDate(value) {
  if (!value) return "unknown";
  return new Date(value).toLocaleString();
}

function RecentDetections({ detections }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Recent Detections</h2>
      </div>

      <div className="table-shell compact">
        <table>
          <thead>
            <tr>
              <th>Repository</th>
              <th>File</th>
              <th>Line</th>
              <th>Type</th>
              <th>Masked Value</th>
              <th>Severity</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Detected</th>
            </tr>
          </thead>
          <tbody>
            {detections.map((detection) => (
              <tr key={detection.id}>
                <td>{detection.repo_full_name}</td>
                <td>{detection.file_path}</td>
                <td>{detection.line_number ?? "unknown"}</td>
                <td>{detection.secret_type}</td>
                <td className="masked-value">{detection.masked_value}</td>
                <td>
                  <StatusBadge value={detection.severity} type="severity" />
                </td>
                <td>{Math.round((detection.confidence_score || 0) * 100)}%</td>
                <td>
                  <StatusBadge value={detection.status} />
                </td>
                <td>{formatDate(detection.detected_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {detections.length === 0 && (
          <div className="empty-state">No recent detections found.</div>
        )}
      </div>
    </section>
  );
}

export default RecentDetections;
