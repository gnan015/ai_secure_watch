import React, { useEffect, useState } from "react";

import AppShell from "../components/AppShell.jsx";
import {
  createDiscordWebhook,
  deleteDiscordWebhook,
  getDiscordWebhooks,
  testDiscordWebhook,
  updateDiscordWebhook,
} from "../services/api.js";

function formatTimestamp(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
}

function DiscordSettings() {
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [nameInput, setNameInput] = useState("Default Discord Webhook");
  const [urlInput, setUrlInput] = useState("");
  const [creating, setCreating] = useState(false);

  const [actionBusyId, setActionBusyId] = useState("");
  const [actionType, setActionType] = useState("");

  async function loadWebhooks() {
    setLoading(true);
    setError("");
    setNotice("");

    try {
      const data = await getDiscordWebhooks();
      setWebhooks(Array.isArray(data) ? data : []);
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Discord webhooks could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWebhooks();
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    if (!urlInput.trim()) {
      setError("Webhook URL is required.");
      return;
    }

    setCreating(true);
    setError("");
    setNotice("");

    try {
      await createDiscordWebhook({
        name: nameInput.trim() || "Default Discord Webhook",
        webhook_url: urlInput.trim(),
      });
      setUrlInput("");
      setNotice("Discord webhook saved.");
      await loadWebhooks();
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail || "Discord webhook could not be saved."
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleToggle(webhook) {
    if (actionBusyId) {
      return;
    }
    setActionBusyId(webhook.id);
    setActionType("toggle");
    setError("");
    setNotice("");

    try {
      const updated = await updateDiscordWebhook(webhook.id, {
        enabled: !webhook.enabled,
      });
      setWebhooks((current) =>
        current.map((item) => (item.id === webhook.id ? updated : item))
      );
      setNotice("Webhook status updated.");
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Discord webhook status could not be updated."
      );
    } finally {
      setActionBusyId("");
      setActionType("");
    }
  }

  async function handleTest(webhook) {
    if (actionBusyId) {
      return;
    }
    setActionBusyId(webhook.id);
    setActionType("test");
    setError("");
    setNotice("");

    try {
      await testDiscordWebhook(webhook.id);
      setNotice("Discord test message sent.");
      await loadWebhooks();
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Discord test message could not be sent."
      );
    } finally {
      setActionBusyId("");
      setActionType("");
    }
  }

  async function handleDelete(webhook) {
    if (actionBusyId) {
      return;
    }
    const shouldDelete = window.confirm(
      `Delete Discord webhook "${webhook.name}"?`
    );
    if (!shouldDelete) {
      return;
    }

    setActionBusyId(webhook.id);
    setActionType("delete");
    setError("");
    setNotice("");

    try {
      await deleteDiscordWebhook(webhook.id);
      setWebhooks((current) => current.filter((item) => item.id !== webhook.id));
      setNotice("Discord webhook deleted.");
    } catch (apiError) {
      setError(
        apiError?.response?.data?.detail ||
          "Discord webhook could not be deleted."
      );
    } finally {
      setActionBusyId("");
      setActionType("");
    }
  }

  return (
    <AppShell
      title="Discord alerts"
      description="Configure encrypted workspace Discord webhook alerting."
      actions={
        <button className="button button-secondary" onClick={loadWebhooks}>
          Refresh
        </button>
      }
    >
      {error && <div className="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}

      <section className="panel form-panel">
        <div className="section-heading">
          <h2>Add Discord webhook</h2>
          <span className="muted">Stored encrypted, displayed masked</span>
        </div>
        <form className="auth-form" onSubmit={handleCreate}>
          <label>
            Name
            <input
              maxLength={200}
              onChange={(event) => setNameInput(event.target.value)}
              type="text"
              value={nameInput}
            />
          </label>
          <label>
            Webhook URL
            <input
              onChange={(event) => setUrlInput(event.target.value)}
              placeholder="https://discord.com/api/webhooks/..."
              required
              type="url"
              value={urlInput}
            />
          </label>
          <button className="button button-primary" disabled={creating} type="submit">
            {creating ? "Saving..." : "Save webhook"}
          </button>
        </form>
      </section>

      {loading ? (
        <div className="loading-state">Loading Discord webhooks...</div>
      ) : webhooks.length === 0 ? (
        <div className="empty-state">
          No Discord webhooks found. Add one to enable workspace alert settings.
        </div>
      ) : (
        <section className="panel">
          <div className="section-heading">
            <h2>Saved webhooks</h2>
            <span className="muted">{webhooks.length} configured</span>
          </div>
          <div className="table-shell">
            <table className="detection-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Webhook</th>
                  <th>Status</th>
                  <th>Last tested</th>
                  <th>Last error</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {webhooks.map((webhook) => {
                  const busy = actionBusyId === webhook.id;
                  return (
                    <tr key={webhook.id}>
                      <td className="strong-cell">{webhook.name}</td>
                      <td className="mono masked-value">
                        ****{webhook.webhook_url_last4 || ""}
                      </td>
                      <td>
                        <span
                          className={
                            webhook.enabled
                              ? "badge badge-completed"
                              : "badge badge-muted"
                          }
                        >
                          {webhook.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </td>
                      <td>{formatTimestamp(webhook.last_tested_at)}</td>
                      <td className={webhook.last_error ? "error-text" : ""}>
                        {webhook.last_error || "-"}
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="button button-secondary compact-button"
                            disabled={busy}
                            onClick={() => handleToggle(webhook)}
                            type="button"
                          >
                            {busy && actionType === "toggle"
                              ? "Updating..."
                              : webhook.enabled
                              ? "Disable"
                              : "Enable"}
                          </button>
                          <button
                            className="button button-secondary compact-button"
                            disabled={busy}
                            onClick={() => handleTest(webhook)}
                            type="button"
                          >
                            {busy && actionType === "test" ? "Testing..." : "Test"}
                          </button>
                          <button
                            className="button button-danger compact-button"
                            disabled={busy}
                            onClick={() => handleDelete(webhook)}
                            type="button"
                          >
                            {busy && actionType === "delete" ? "Deleting..." : "Delete"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </AppShell>
  );
}

export default DiscordSettings;
