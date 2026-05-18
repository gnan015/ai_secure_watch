import React from "react";

const summaryItems = [
  { label: "Total detections", key: "total_detections" },
  { label: "Open detections", key: "open_detections" },
  { label: "Critical detections", key: "critical_count", tone: "critical" },
  { label: "High detections", key: "high_count", tone: "high" },
  { label: "Medium detections", key: "medium_count", tone: "medium" },
  { label: "Resolved detections", key: "resolved_detections", tone: "resolved" },
];

function SummaryCards({ summary }) {
  return (
    <section className="summary-grid" aria-label="Detection summary">
      {summaryItems.map((item) => (
        <div className={`summary-card ${item.tone || ""}`} key={item.key}>
          <span>{item.label}</span>
          <strong>{summary?.[item.key] ?? 0}</strong>
        </div>
      ))}
    </section>
  );
}

export default SummaryCards;
