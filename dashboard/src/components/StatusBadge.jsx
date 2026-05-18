import React from "react";

const severityClassNames = {
  CRITICAL: "badge badge-critical",
  HIGH: "badge badge-high",
  MEDIUM: "badge badge-medium",
  LOW: "badge badge-low",
};

const statusClassNames = {
  open: "badge badge-open",
  resolved: "badge badge-resolved",
  dismissed: "badge badge-dismissed",
};

function StatusBadge({ value, type = "status" }) {
  const normalizedValue =
    type === "severity" ? String(value || "").toUpperCase() : String(value || "");
  const className =
    type === "severity"
      ? severityClassNames[normalizedValue] || "badge badge-muted"
      : statusClassNames[normalizedValue] || "badge badge-muted";

  return <span className={className}>{normalizedValue || "unknown"}</span>;
}

export default StatusBadge;
