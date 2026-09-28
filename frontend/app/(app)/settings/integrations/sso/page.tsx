"use client";

import React, { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function SSOSettingsPage() {
  const { data: configs, isLoading } = useSWR("/v3/integrations/identity/configs", fetcher);

  const [providerName, setProviderName] = useState("");
  const [protocol, setProtocol] = useState("OIDC");
  const [issuer, setIssuer] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [samlMetadata, setSamlMetadata] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v3/integrations/identity/configs", {
        provider_name: providerName,
        protocol,
        issuer: protocol === "OIDC" ? issuer : undefined,
        client_id: protocol === "OIDC" ? clientId : undefined,
        client_secret: protocol === "OIDC" && clientSecret ? clientSecret : undefined,
        saml_metadata: protocol === "SAML" ? samlMetadata : undefined,
      });
      setShowAddForm(false);
      setProviderName("");
      setIssuer("");
      setClientId("");
      setClientSecret("");
      setSamlMetadata("");
      mutate("/v3/integrations/identity/configs");
    } catch (err: any) {
      alert("Failed to save SSO config: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SSO & Identity Federation</h1>
          <p className="text-sm text-gray-500">Configure SAML 2.0 and OpenID Connect (OIDC) identity providers.</p>
        </div>
        <div className="flex gap-4 items-center">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
          >
            {showAddForm ? "Cancel" : "+ Add Identity Provider"}
          </button>
          <Link href="/settings/integrations" className="text-sm text-indigo-600 hover:underline">
            ← Hub
          </Link>
        </div>
      </div>

      {showAddForm && (
        <form onSubmit={handleCreate} className="p-6 bg-white rounded-lg border shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-900">New Identity Provider Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700">Provider Name</label>
              <input
                type="text"
                required
                placeholder="e.g. Okta Workforce SSO"
                value={providerName}
                onChange={(e) => setProviderName(e.target.value)}
                className="mt-1 w-full p-2 border rounded text-xs bg-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700">Protocol</label>
              <select
                value={protocol}
                onChange={(e) => setProtocol(e.target.value)}
                className="mt-1 w-full p-2 border rounded text-xs bg-white"
              >
                <option value="OIDC">OpenID Connect (OIDC)</option>
                <option value="SAML">SAML 2.0</option>
              </select>
            </div>
          </div>

          {protocol === "OIDC" ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Issuer URL</label>
                <input
                  type="url"
                  placeholder="https://identity.company.com"
                  value={issuer}
                  onChange={(e) => setIssuer(e.target.value)}
                  className="mt-1 w-full p-2 border rounded text-xs bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Client ID</label>
                <input
                  type="text"
                  placeholder="Client Identifier"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  className="mt-1 w-full p-2 border rounded text-xs bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Client Secret</label>
                <input
                  type="password"
                  placeholder="Encrypted symmetrically"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  className="mt-1 w-full p-2 border rounded text-xs bg-white"
                />
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-semibold text-gray-700">SAML Metadata XML</label>
              <textarea
                rows={4}
                placeholder="<EntityDescriptor ...> ... </EntityDescriptor>"
                value={samlMetadata}
                onChange={(e) => setSamlMetadata(e.target.value)}
                className="mt-1 w-full p-2 border rounded text-xs font-mono bg-white"
              />
            </div>
          )}

          <button
            type="submit"
            className="px-4 py-2 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
          >
            Save Configuration
          </button>
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {configs && configs.map((c: any) => (
          <div key={c.id} className="p-5 border rounded-xl bg-white shadow-sm space-y-2">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-gray-900">{c.provider_name}</h3>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-800">{c.protocol}</span>
            </div>
            <div className="text-xs text-gray-600 space-y-1">
              {c.issuer && <div><strong>Issuer:</strong> {c.issuer}</div>}
              {c.client_id && <div><strong>Client ID:</strong> {c.client_id}</div>}
              <div><strong>Vault Secret:</strong> {c.has_secret ? "Stored & Encrypted" : "None"}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
