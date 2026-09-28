"use client";

import React, { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function IntegrationsHubPage() {
  const { data: providers } = useSWR("/v3/integrations/providers", fetcher);
  const { data: connections } = useSWR("/v3/integrations/connections", fetcher);
  const { data: idpConfigs } = useSWR("/v3/integrations/identity/configs", fetcher);
  const { data: scimConfig } = useSWR("/v3/integrations/scim/config", fetcher);
  const { data: apiKeys } = useSWR("/v3/integrations/api-keys", fetcher);
  const { data: webhooks } = useSWR("/v3/integrations/webhooks", fetcher);
  const { data: outboxEvents } = useSWR("/v3/integrations/outbox?limit=10", fetcher);

  const [activeTab, setActiveTab] = useState<
    "overview" | "connections" | "sso" | "scim" | "apikeys" | "webhooks" | "logs"
  >("overview");

  // New Connection Form State
  const [newConnName, setNewConnName] = useState("");
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [connSecret, setConnSecret] = useState("");
  const [showAddConnModal, setShowAddConnModal] = useState(false);

  // New API Key Form State
  const [newKeyName, setNewKeyName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["employee:read"]);
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);

  // Webhook Form State
  const [webhookName, setWebhookName] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookEvents, setWebhookEvents] = useState("employee.onboarded,employee.offboarded");

  // Telemetry / Message state
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleCreateConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v3/integrations/connections", {
        name: newConnName,
        provider_id: selectedProviderId,
        environment: "PRODUCTION",
        secret_value: connSecret || undefined,
      });
      setShowAddConnModal(false);
      setNewConnName("");
      setConnSecret("");
      mutate("/v3/integrations/connections");
      setStatusMessage("Connection created successfully.");
    } catch (err: any) {
      alert("Failed to create connection: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleTestConnection = async (id: string) => {
    try {
      const resp = await api.post(`/v3/integrations/connections/${id}/test`, {});
      alert(`Test Result: ${resp.data.message} (Latency: ${resp.data.latency_ms}ms)`);
      mutate("/v3/integrations/connections");
    } catch (err: any) {
      alert("Connection test failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleCreateAPIKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await api.post("/v3/integrations/api-keys", {
        name: newKeyName,
        scopes: selectedScopes,
      });
      setCreatedRawKey(resp.data.raw_api_key);
      setNewKeyName("");
      mutate("/v3/integrations/api-keys");
    } catch (err: any) {
      alert("Failed to create API Key: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleRotateKey = async (id: string) => {
    if (!confirm("Are you sure you want to rotate this key? The existing key will stop working immediately.")) return;
    try {
      const resp = await api.post(`/v3/integrations/api-keys/${id}/rotate`, {});
      alert(`Key rotated! New Raw Key: ${resp.data.new_raw_api_key}`);
      mutate("/v3/integrations/api-keys");
    } catch (err: any) {
      alert("Rotation failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleRevokeKey = async (id: string) => {
    if (!confirm("Revoke this API Key permanently?")) return;
    try {
      await api.delete(`/v3/integrations/api-keys/${id}`);
      mutate("/v3/integrations/api-keys");
      setStatusMessage("API Key revoked successfully.");
    } catch (err: any) {
      alert("Revocation failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v3/integrations/webhooks", {
        name: webhookName,
        url: webhookUrl,
        subscribed_events: webhookEvents.split(",").map((s) => s.trim()),
      });
      setWebhookName("");
      setWebhookUrl("");
      mutate("/v3/integrations/webhooks");
      setStatusMessage("Webhook endpoint registered successfully.");
    } catch (err: any) {
      alert("Failed to create webhook: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleTestWebhook = async (id: string) => {
    try {
      const resp = await api.post(`/v3/integrations/webhooks/${id}/test`, {});
      alert(`Test ping status: ${resp.data.message}`);
      mutate("/v3/integrations/webhooks");
    } catch (err: any) {
      alert("Webhook test failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleProcessOutbox = async () => {
    try {
      const resp = await api.post("/v3/integrations/outbox/process", {});
      alert(`Outbox batch executed: Processed ${resp.data.processed_count} events, Created ${resp.data.deliveries_created} deliveries.`);
      mutate("/v3/integrations/outbox?limit=10");
    } catch (err: any) {
      alert("Outbox process failed: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Enterprise IAM & Integration Hub
          </h1>
          <p className="text-sm text-gray-500">
            Enterprise Identity Federation, SCIM 2.0 Provisioning, Scoped API Keys, and Outbound Webhooks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleProcessOutbox}
            className="px-3 py-1.5 text-xs font-semibold rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
          >
            Flush Outbox Queue
          </button>
          <button
            onClick={() => {
              if (providers && providers.length > 0) setSelectedProviderId(providers[0].id);
              setShowAddConnModal(true);
            }}
            className="px-4 py-2 text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
          >
            + Connect System
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 text-sm bg-green-50 border border-green-200 text-green-700 rounded-md flex justify-between">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="font-bold">✕</button>
        </div>
      )}

      {/* Metric Cards Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div className="p-4 bg-white rounded-lg border shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase">Connections</span>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {connections ? connections.length : 0}
          </div>
          <span className="text-xs text-green-600 font-medium">Active Integrations</span>
        </div>
        <div className="p-4 bg-white rounded-lg border shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase">SSO Providers</span>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {idpConfigs ? idpConfigs.length : 0}
          </div>
          <span className="text-xs text-indigo-600 font-medium">OIDC / SAML 2.0</span>
        </div>
        <div className="p-4 bg-white rounded-lg border shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase">SCIM Status</span>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {scimConfig?.enabled ? "Enabled" : "Configured"}
          </div>
          <span className="text-xs text-blue-600 font-medium">RFC 7644 Inbound</span>
        </div>
        <div className="p-4 bg-white rounded-lg border shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase">Active API Keys</span>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {apiKeys ? apiKeys.filter((k: any) => !k.revoked_at).length : 0}
          </div>
          <span className="text-xs text-purple-600 font-medium">Hashed & Scoped</span>
        </div>
        <div className="p-4 bg-white rounded-lg border shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase">Webhooks</span>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {webhooks ? webhooks.length : 0}
          </div>
          <span className="text-xs text-emerald-600 font-medium">HMAC Signed</span>
        </div>
        <div className="p-4 bg-white rounded-lg border shadow-sm">
          <span className="text-xs font-medium text-gray-500 uppercase">Outbox Backlog</span>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {outboxEvents ? outboxEvents.filter((e: any) => e.status === "PENDING").length : 0}
          </div>
          <span className="text-xs text-amber-600 font-medium">Transactional</span>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b space-x-6 text-sm font-medium">
        {[
          { key: "overview", label: "Overview & Catalog" },
          { key: "connections", label: "Connections" },
          { key: "sso", label: "SSO & Identity" },
          { key: "scim", label: "SCIM 2.0" },
          { key: "apikeys", label: "API Keys" },
          { key: "webhooks", label: "Webhooks" },
          { key: "logs", label: "Outbox & Logs" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`pb-3 transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-indigo-600 text-indigo-600 font-semibold"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: Overview & Catalog */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg border shadow-sm">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Integration Catalog</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {providers && providers.map((p: any) => (
                <div key={p.id} className="p-4 rounded-lg border bg-gray-50 hover:bg-gray-100 transition flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start">
                      <span className="text-xs px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 font-medium">
                        {p.category}
                      </span>
                      <span className="text-xs text-gray-500">{p.provider_type}</span>
                    </div>
                    <h3 className="font-semibold text-gray-900 mt-2">{p.name}</h3>
                    <p className="text-xs text-gray-600 mt-1">{p.description}</p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedProviderId(p.id);
                      setNewConnName(`${p.name} Production`);
                      setShowAddConnModal(true);
                    }}
                    className="mt-4 w-full py-1.5 text-xs font-medium rounded border border-indigo-600 text-indigo-600 hover:bg-indigo-50"
                  >
                    Setup Integration
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Connections */}
      {activeTab === "connections" && (
        <div className="bg-white rounded-lg border shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-base font-semibold text-gray-900">Configured External Connections</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
                <tr>
                  <th className="py-2.5 px-4">Connection Name</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Environment</th>
                  <th className="py-2.5 px-4">Credentials</th>
                  <th className="py-2.5 px-4">Last Success</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {connections && connections.length > 0 ? (
                  connections.map((c: any) => (
                    <tr key={c.id} className="hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium text-gray-900">{c.name}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          c.status === "ACTIVE" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-xs text-gray-600">{c.environment}</td>
                      <td className="py-3 px-4 text-xs">
                        {c.has_credentials ? (
                          <span className="text-emerald-700 font-medium">✓ Encrypted Vault</span>
                        ) : (
                          <span className="text-gray-400">None</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs text-gray-500">
                        {c.last_success_at ? new Date(c.last_success_at).toLocaleTimeString() : "Never"}
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => handleTestConnection(c.id)}
                          className="px-2.5 py-1 text-xs border rounded text-indigo-600 hover:bg-indigo-50"
                        >
                          Test
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="text-center py-6 text-gray-500">
                      No connections configured yet. Click "Connect System" to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SSO & Identity Federation */}
      {activeTab === "sso" && (
        <div className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-gray-900">SAML 2.0 & OIDC Identity Providers</h2>
            <p className="text-xs text-gray-500 mt-1">
              Configure federated single sign-on with Azure AD, Okta, Google, or custom IdPs.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {idpConfigs && idpConfigs.map((idp: any) => (
              <div key={idp.id} className="p-4 border rounded-lg bg-gray-50 space-y-2">
                <div className="flex justify-between items-center">
                  <h3 className="font-semibold text-gray-900">{idp.provider_name}</h3>
                  <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded">{idp.protocol}</span>
                </div>
                <div className="text-xs text-gray-600 space-y-1">
                  <div><strong>Issuer:</strong> {idp.issuer || "N/A"}</div>
                  <div><strong>Client ID:</strong> {idp.client_id || "N/A"}</div>
                  <div><strong>Secret Status:</strong> {idp.has_secret ? "Encrypted in Vault" : "Not Set"}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: SCIM 2.0 Inbound Provisioning */}
      {activeTab === "scim" && (
        <div className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-gray-900">RFC 7644 SCIM 2.0 Inbound Provisioning</h2>
            <p className="text-xs text-gray-500 mt-1">
              Automate user onboarding, attribute updates, and deprovisioning from Microsoft Entra ID or Okta.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-gray-50 border space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <strong>SCIM Base URL:</strong>
                <div className="p-2 bg-white rounded border font-mono mt-1">
                  https://app.zeramai.com/api/v3/scim/v2
                </div>
              </div>
              <div>
                <strong>Bearer Token Status:</strong>
                <div className="p-2 bg-white rounded border font-mono mt-1 text-green-700">
                  {scimConfig?.has_bearer_token ? "✓ Active (AES-256 Encrypted)" : "Not Configured"}
                </div>
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={async () => {
                  try {
                    const resp = await api.post("/v3/integrations/scim/config/rotate-token", {});
                    alert(resp.data.message + "\n\nToken: " + resp.data.bearer_token);
                    mutate("/v3/integrations/scim/config");
                  } catch (err: any) {
                    alert("Token rotation failed: " + (err.response?.data?.detail || err.message));
                  }
                }}
                className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
              >
                Rotate Bearer Token
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: API Keys */}
      {activeTab === "apikeys" && (
        <div className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-base font-semibold text-gray-900">Server-to-Server API Keys</h2>
              <p className="text-xs text-gray-500 mt-1">
                Raw keys are shown only once upon creation. Only SHA-256 hashes are stored.
              </p>
            </div>
          </div>

          {createdRawKey && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-md space-y-2">
              <span className="text-xs font-bold text-amber-900">
                ⚠ SAVE THIS KEY NOW — IT WILL NEVER BE SHOWN AGAIN:
              </span>
              <div className="p-2 bg-white rounded border font-mono text-sm text-gray-900 break-all select-all">
                {createdRawKey}
              </div>
              <button
                onClick={() => setCreatedRawKey(null)}
                className="text-xs text-amber-800 underline"
              >
                I have safely stored this key
              </button>
            </div>
          )}

          <form onSubmit={handleCreateAPIKey} className="p-4 bg-gray-50 rounded-lg border space-y-3">
            <h3 className="text-xs font-bold text-gray-700 uppercase">Generate New API Key</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input
                type="text"
                required
                placeholder="Key Name (e.g. Payroll Exporter)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="p-2 border rounded text-xs bg-white"
              />
              <input
                type="text"
                placeholder="Scopes comma-separated (e.g. employee:read, payroll:read)"
                value={selectedScopes.join(", ")}
                onChange={(e) => setSelectedScopes(e.target.value.split(",").map((s) => s.trim()))}
                className="p-2 border rounded text-xs bg-white"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
            >
              Generate Key
            </button>
          </form>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
                <tr>
                  <th className="py-2.5 px-4">Key Name</th>
                  <th className="py-2.5 px-4">Prefix</th>
                  <th className="py-2.5 px-4">Scopes</th>
                  <th className="py-2.5 px-4">Created</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {apiKeys && apiKeys.map((k: any) => (
                  <tr key={k.id} className="hover:bg-gray-50 text-xs">
                    <td className="py-3 px-4 font-medium text-gray-900">{k.name}</td>
                    <td className="py-3 px-4 font-mono">{k.key_prefix}••••</td>
                    <td className="py-3 px-4">{k.scopes?.join(", ")}</td>
                    <td className="py-3 px-4 text-gray-500">{new Date(k.created_at).toLocaleDateString()}</td>
                    <td className="py-3 px-4">
                      {k.revoked_at ? (
                        <span className="text-red-600 font-medium">Revoked</span>
                      ) : (
                        <span className="text-green-600 font-medium">Active</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      {!k.revoked_at && (
                        <>
                          <button
                            onClick={() => handleRotateKey(k.id)}
                            className="text-indigo-600 hover:underline"
                          >
                            Rotate
                          </button>
                          <button
                            onClick={() => handleRevokeKey(k.id)}
                            className="text-red-600 hover:underline"
                          >
                            Revoke
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 6: Webhooks */}
      {activeTab === "webhooks" && (
        <div className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Outbound Webhooks Platform</h2>
            <p className="text-xs text-gray-500 mt-1">
              HMAC-SHA256 signed event notifications with replay protection.
            </p>
          </div>

          <form onSubmit={handleCreateWebhook} className="p-4 bg-gray-50 rounded-lg border space-y-3">
            <h3 className="text-xs font-bold text-gray-700 uppercase">Register Webhook Endpoint</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input
                type="text"
                required
                placeholder="Endpoint Name (e.g. ERP Onboarding Sync)"
                value={webhookName}
                onChange={(e) => setNewConnName(e.target.value)}
                className="p-2 border rounded text-xs bg-white"
              />
              <input
                type="url"
                required
                placeholder="https://api.yourcompany.com/webhooks"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="p-2 border rounded text-xs bg-white"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
            >
              Register Webhook
            </button>
          </form>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
                <tr>
                  <th className="py-2.5 px-4">Name</th>
                  <th className="py-2.5 px-4">URL</th>
                  <th className="py-2.5 px-4">Subscribed Events</th>
                  <th className="py-2.5 px-4">Last Delivery</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {webhooks && webhooks.map((w: any) => (
                  <tr key={w.id} className="hover:bg-gray-50 text-xs">
                    <td className="py-3 px-4 font-medium text-gray-900">{w.name}</td>
                    <td className="py-3 px-4 font-mono text-gray-600">{w.url}</td>
                    <td className="py-3 px-4">{w.subscribed_events?.join(", ")}</td>
                    <td className="py-3 px-4 text-gray-500">
                      {w.last_delivery_at ? new Date(w.last_delivery_at).toLocaleTimeString() : "Never"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleTestWebhook(w.id)}
                        className="px-2 py-1 border rounded text-indigo-600 hover:bg-indigo-50"
                      >
                        Send Ping
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 7: Outbox & Logs */}
      {activeTab === "logs" && (
        <div className="bg-white rounded-lg border shadow-sm p-6 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-base font-semibold text-gray-900">Transactional Outbox & Execution Telemetry</h2>
              <p className="text-xs text-gray-500 mt-1">Real-time status of asynchronous events and external sync calls.</p>
            </div>
            <button
              onClick={handleProcessOutbox}
              className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
            >
              Trigger Outbox Batch
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
                <tr>
                  <th className="py-2.5 px-4">Event Type</th>
                  <th className="py-2.5 px-4">Aggregate</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Retries</th>
                  <th className="py-2.5 px-4">Available At</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {outboxEvents && outboxEvents.map((evt: any) => (
                  <tr key={evt.id} className="hover:bg-gray-50 text-xs">
                    <td className="py-3 px-4 font-mono font-medium text-gray-900">{evt.event_type}</td>
                    <td className="py-3 px-4">{evt.aggregate_type} ({evt.aggregate_id.slice(0, 8)}...)</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        evt.status === "PROCESSED" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {evt.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">{evt.retry_count}</td>
                    <td className="py-3 px-4 text-gray-500">{new Date(evt.available_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Connection Modal */}
      {showAddConnModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900">Add Integration Connection</h3>
            <form onSubmit={handleCreateConnection} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Provider</label>
                <select
                  value={selectedProviderId}
                  onChange={(e) => setSelectedProviderId(e.target.value)}
                  className="mt-1 w-full p-2 border rounded text-xs bg-white"
                >
                  {providers && providers.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Connection Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Entra ID Production Directory"
                  value={newConnName}
                  onChange={(e) => setNewConnName(e.target.value)}
                  className="mt-1 w-full p-2 border rounded text-xs bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Credential / Secret (Optional)</label>
                <input
                  type="password"
                  placeholder="Client secret, API key, or token (AES encrypted)"
                  value={connSecret}
                  onChange={(e) => setConnSecret(e.target.value)}
                  className="mt-1 w-full p-2 border rounded text-xs bg-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddConnModal(false)}
                  className="px-3 py-1.5 text-xs border rounded text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  Connect
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
