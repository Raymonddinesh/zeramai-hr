"use client";

import React, { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function APIKeysPage() {
  const { data: keys, isLoading } = useSWR("/v3/integrations/api-keys", fetcher);

  const [name, setName] = useState("");
  const [scopes, setScopes] = useState("employee:read, payroll:read");
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await api.post("/v3/integrations/api-keys", {
        name,
        scopes: scopes.split(",").map((s) => s.trim()),
      });
      setCreatedRawKey(resp.data.raw_api_key);
      setName("");
      mutate("/v3/integrations/api-keys");
    } catch (err: any) {
      alert("Failed to generate key: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm("Revoke this API Key immediately?")) return;
    try {
      await api.delete(`/v3/integrations/api-keys/${id}`);
      mutate("/v3/integrations/api-keys");
    } catch (err: any) {
      alert("Revocation failed: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Key Management</h1>
          <p className="text-sm text-gray-500">Secure tokens for programmatic server-to-server access.</p>
        </div>
        <Link href="/settings/integrations" className="text-sm text-indigo-600 hover:underline">
          ← Back to Hub
        </Link>
      </div>

      {createdRawKey && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg space-y-2">
          <span className="text-xs font-bold text-amber-900">NEW API KEY GENERATED:</span>
          <div className="p-2 bg-white rounded border font-mono text-sm break-all select-all">
            {createdRawKey}
          </div>
          <button onClick={() => setCreatedRawKey(null)} className="text-xs text-amber-800 underline">
            Dismiss
          </button>
        </div>
      )}

      <form onSubmit={handleCreate} className="p-5 bg-white rounded-xl border shadow-sm space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Create Scoped API Key</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            required
            placeholder="Key Name (e.g. BI Pipeline)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="p-2 border rounded text-xs bg-white"
          />
          <input
            type="text"
            placeholder="Scopes comma-separated"
            value={scopes}
            onChange={(e) => setScopes(e.target.value)}
            className="p-2 border rounded text-xs bg-white"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
        >
          Generate Key
        </button>
      </form>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-gray-50 border-b text-gray-500 uppercase">
            <tr>
              <th className="py-3 px-4">Name</th>
              <th className="py-3 px-4">Prefix</th>
              <th className="py-3 px-4">Scopes</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {keys && keys.map((k: any) => (
              <tr key={k.id} className="hover:bg-gray-50">
                <td className="py-3 px-4 font-semibold text-gray-900">{k.name}</td>
                <td className="py-3 px-4 font-mono text-gray-600">{k.key_prefix}••••</td>
                <td className="py-3 px-4">{k.scopes?.join(", ")}</td>
                <td className="py-3 px-4">
                  {k.revoked_at ? (
                    <span className="text-red-600 font-medium">Revoked</span>
                  ) : (
                    <span className="text-green-600 font-medium">Active</span>
                  )}
                </td>
                <td className="py-3 px-4 text-right">
                  {!k.revoked_at && (
                    <button
                      onClick={() => handleRevoke(k.id)}
                      className="text-red-600 hover:underline"
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
