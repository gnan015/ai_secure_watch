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

export async function getGitHubInstallations() {
  const response = await apiClient.get("/api/github/installations");
  return response.data;
}

export async function saveGitHubInstallation(installationId) {
  const response = await apiClient.post("/api/github/installations", {
    installation_id: Number(installationId),
  });
  return response.data;
}

export async function syncGitHubInstallationRepositories(installationId) {
  const response = await apiClient.post(
    `/api/github/installations/${installationId}/sync-repositories`
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

export async function getDiscordWebhooks() {
  const response = await apiClient.get("/api/discord/webhooks");
  return response.data;
}

export async function createDiscordWebhook({ name, webhook_url }) {
  const response = await apiClient.post("/api/discord/webhooks", {
    name,
    webhook_url,
  });
  return response.data;
}

export async function updateDiscordWebhook(webhookId, payload) {
  const response = await apiClient.patch(
    `/api/discord/webhooks/${webhookId}`,
    payload
  );
  return response.data;
}

export async function deleteDiscordWebhook(webhookId) {
  const response = await apiClient.delete(`/api/discord/webhooks/${webhookId}`);
  return response.data;
}

export async function testDiscordWebhook(webhookId) {
  const response = await apiClient.post(
    `/api/discord/webhooks/${webhookId}/test`
  );
  return response.data;
}

export async function getV2DashboardOverview() {
  const response = await apiClient.get("/api/v2/dashboard/overview");
  return response.data;
}

export async function getV2ScanEvents(params = {}) {
  const response = await apiClient.get("/api/v2/scan-events", { params });
  return response.data;
}

export async function getV2Detections(params = {}) {
  const response = await apiClient.get("/api/v2/detections", { params });
  return response.data;
}

export async function updateV2DetectionStatus(detectionId, status) {
  const response = await apiClient.patch(
    `/api/v2/detections/${detectionId}/status`,
    { status }
  );
  return response.data;
}
