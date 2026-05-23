import React from "react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import DetectionTable from "../components/DetectionTable.jsx";
import RecentDetections from "../components/RecentDetections.jsx";
import SecretTypeChart from "../components/SecretTypeChart.jsx";
import SeverityChart from "../components/SeverityChart.jsx";
import SummaryCards from "../components/SummaryCards.jsx";
import TrendChart from "../components/TrendChart.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  fetchDetections,
  fetchRecentDetections,
  fetchSecretTypeStats,
  fetchSeverityStats,
  fetchSummaryStats,
  fetchTrendStats,
  getV2DashboardOverview,
  updateDetectionStatus,
} from "../services/api.js";

const initialFilters = {
  severity: "",
  status: "",
  repo: "",
};

function Dashboard() {
  const navigate = useNavigate();
  const { signOut } = useAuth();
  const [v2Overview, setV2Overview] = useState(null);
  const [summary, setSummary] = useState(null);
  const [recentDetections, setRecentDetections] = useState([]);
  const [detections, setDetections] = useState([]);
  const [severityStats, setSeverityStats] = useState([]);
  const [secretTypeStats, setSecretTypeStats] = useState([]);
  const [trendStats, setTrendStats] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState("");
  const [signingOut, setSigningOut] = useState(false);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [
        summaryData,
        recentData,
        detectionsData,
        severityData,
        secretTypeData,
        trendData,
        v2OverviewData,
      ] = await Promise.all([
        fetchSummaryStats(),
        fetchRecentDetections(10),
        fetchDetections({ ...filters, limit: 100 }),
        fetchSeverityStats(),
        fetchSecretTypeStats(),
        fetchTrendStats(),
        getV2DashboardOverview(),
      ]);

      setV2Overview(v2OverviewData);
      setSummary(summaryData);
      setRecentDetections(recentData);
      setDetections(detectionsData);
      setSeverityStats(severityData);
      setSecretTypeStats(secretTypeData);
      setTrendStats(trendData);
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Dashboard data could not be loaded. Check that the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  function handleFilterChange(key, value) {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [key]: value,
    }));
  }

  async function handleStatusChange(detectionId, status) {
    setUpdatingId(detectionId);
    setError("");

    try {
      await updateDetectionStatus(detectionId, status);
      await loadDashboardData();
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Detection status could not be updated."
      );
    } finally {
      setUpdatingId("");
    }
  }

  async function handleSignOut() {
    setSigningOut(true);
    setError("");

    const { error: signOutError } = await signOut();

    if (signOutError) {
      setError(signOutError.message || "Sign out failed. Please try again.");
      setSigningOut(false);
      return;
    }

    navigate("/login", { replace: true });
  }

  return (
    <main className="dashboard">
      <header className="hero">
        <div>
          <h1>AI SecureWatch</h1>
          <p>Real-time GitHub credential leak monitoring dashboard</p>
        </div>
        <div className="header-actions">
          <Link className="refresh-button" to="/repositories">
            Repositories
          </Link>
          <Link className="refresh-button" to="/integrations/discord">
            Discord
          </Link>
          <Link className="refresh-button" to="/scan-events">
            Scan Events
          </Link>
          <Link className="refresh-button" to="/detections">
            Detections
          </Link>
          <button className="refresh-button" onClick={loadDashboardData}>
            Refresh
          </button>
          <button
            className="sign-out-button"
            disabled={signingOut}
            onClick={handleSignOut}
            type="button"
          >
            {signingOut ? "Signing out..." : "Sign out"}
          </button>
        </div>
      </header>

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
              <span>Latest scan</span>
              <strong className="timestamp-value">
                {v2Overview?.latest_scan_at
                  ? new Date(v2Overview.latest_scan_at).toLocaleDateString()
                  : "-"}
              </strong>
            </article>
          </section>

          <SummaryCards summary={summary} />
          <RecentDetections detections={recentDetections} />

          <section className="chart-grid" aria-label="Detection charts">
            <SeverityChart data={severityStats} />
            <SecretTypeChart data={secretTypeStats} />
            <TrendChart data={trendStats} />
          </section>

          <DetectionTable
            detections={detections}
            filters={filters}
            onFilterChange={handleFilterChange}
            onStatusChange={handleStatusChange}
            updatingId={updatingId}
          />
        </>
      )}
    </main>
  );
}

export default Dashboard;
