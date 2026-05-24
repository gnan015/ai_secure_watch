import React from "react";
import { useCallback, useEffect, useState } from "react";

import AppShell from "../components/AppShell.jsx";
import { getV2DashboardOverview } from "../services/api.js";

function Dashboard() {
  const [v2Overview, setV2Overview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const v2OverviewData = await getV2DashboardOverview();
      setV2Overview(v2OverviewData);
    } catch (apiError) {
      setV2Overview(null);
      setError(
        apiError?.response?.data?.detail ||
          "Dashboard data could not be loaded. Check that the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  return (
    <AppShell
      title="Security overview"
      description="Real-time GitHub App monitoring for workspace secret exposure."
      actions={
        <button className="button button-secondary" onClick={loadDashboardData}>
            Refresh
          </button>
      }
    >
      {error && <div className="alert">{error}</div>}

      {loading ? (
        <div className="loading-state">Loading dashboard data...</div>
      ) : (
        <>
          <section className="summary-grid" aria-label="V2 overview">
            <article className="summary-card">
              <span>Total repositories</span>
              <strong>{v2Overview?.total_repositories ?? 0}</strong>
            </article>
            <article className="summary-card resolved">
              <span>Monitored repositories</span>
              <strong>{v2Overview?.monitored_repositories ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>Total scan events</span>
              <strong>{v2Overview?.total_scan_events ?? 0}</strong>
            </article>
            <article className="summary-card high">
              <span>Failed scan events</span>
              <strong>{v2Overview?.failed_scan_events ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>Total detections</span>
              <strong>{v2Overview?.total_detections ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>Open detections</span>
              <strong>{v2Overview?.open_detections ?? 0}</strong>
            </article>
            <article className="summary-card critical">
              <span>Critical detections</span>
              <strong>{v2Overview?.critical_detections ?? 0}</strong>
            </article>
            <article className="summary-card high">
              <span>High detections</span>
              <strong>{v2Overview?.high_detections ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>Medium detections</span>
              <strong>{v2Overview?.medium_detections ?? 0}</strong>
            </article>
            <article className="summary-card resolved">
              <span>Resolved detections</span>
              <strong>{v2Overview?.resolved_detections ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>Latest scan</span>
              <strong className="timestamp-value">
                {v2Overview?.latest_scan_at
                  ? new Date(v2Overview.latest_scan_at).toLocaleDateString()
                  : "-"}
              </strong>
            </article>
          </section>
        </>
      )}
    </AppShell>
  );
}

export default Dashboard;
