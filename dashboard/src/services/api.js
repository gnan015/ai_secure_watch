import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  timeout: 15000,
});

export async function fetchDetections(filters = {}) {
  const params = {};

  if (filters.status) params.status = filters.status;
  if (filters.severity) params.severity = filters.severity;
  if (filters.repo) params.repo = filters.repo;
  if (filters.limit) params.limit = filters.limit;

  const response = await apiClient.get("/api/detections", { params });
  return response.data;
}

export async function fetchRecentDetections(limit = 10) {
  const response = await apiClient.get("/api/detections/recent", {
    params: { limit },
  });
  return response.data;
}

export async function fetchSummaryStats() {
  const response = await apiClient.get("/api/stats/summary");
  return response.data;
}

export async function fetchSeverityStats() {
  const response = await apiClient.get("/api/stats/severity");
  return response.data;
}

export async function fetchSecretTypeStats() {
  const response = await apiClient.get("/api/stats/secret-types");
  return response.data;
}

export async function fetchTrendStats() {
  const response = await apiClient.get("/api/stats/trends");
  return response.data;
}

export async function updateDetectionStatus(detectionId, status) {
  const response = await apiClient.patch(
    `/api/detections/${detectionId}/status`,
    { status }
  );
  return response.data;
}
