import axios from "axios";

import supabase from "../lib/supabase.js";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  timeout: 15000,
});

apiClient.interceptors.request.use(async (config) => {
  try {
    const { data, error } = await supabase.auth.getSession();

    if (error) {
      console.warn("Supabase session could not be read for API request.");
      return config;
    }

    const accessToken = data?.session?.access_token;

    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
  } catch (sessionError) {
    console.warn("Supabase session lookup failed before API request.");
  }

  return config;
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

export async function getRepositories() {
  const response = await apiClient.get("/api/repositories");
  return response.data;
}

export async function updateRepositoryMonitoring(
  repositoryId,
  monitoringEnabled
) {
  const response = await apiClient.patch(
    `/api/repositories/${repositoryId}/monitoring`,
    { monitoring_enabled: monitoringEnabled }
  );
  return response.data;
}
