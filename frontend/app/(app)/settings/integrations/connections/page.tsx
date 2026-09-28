"use client";

import React, { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function IntegrationConnectionsPage() {
  const { data: connections, isLoading } = useSWR("/v3/integrations/connections", fetcher);
  const { data: providers } = useSWR("/v3/integrations/providers", fetcher);

  const [testResult, setTestResult] = useState<string | null>(null);

  const handleTest = async (id: string) => {
    try {
      const resp = await api.post(`/v3/integrations/connections/${id}/test`, {});
      setTestResult(`Test Success: ${resp.data.message} (${resp.data.latency_ms}ms)`);
      mutate("/v3/integrations/connections");
    } catch (err: any) {
      setTestResult(`Test Failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configured External Connections</h1>
          <p className="text-sm text-gray-500">Live connectors with health checks, credentials, and telemetry.</p>
        </div>
        <Link
          href="/settings/integrations"
          className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        >
          ← Back to Integration Hub
        </Link>
      </div>

      {testResult && (
        <div className="p-3 text-sm bg-blue-50 border border-blue-200 text-blue-800 rounded-md flex justify-between">
          <span>{testResult}</span>
          <button onClick={() => setTestResult(null)} className="font-bold">✕</button>
        </div>
      )}

      <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
            <tr>
              <th className="py-3 px-4">Connection</th>
              <th className="py-3 px-4">Environment</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Credentials Vault</th>
              <th className="py-3 px-4">Last Success</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {connections && connections.map((c: any) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="py-3 px-4 font-semibold text-gray-900">{c.name}</td>
                <td className="py-3 px-4 text-xs font-mono">{c.environment}</td>
                <td className="py-3 px-4">
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    c.status === "ACTIVE" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                  }`}>
                    {c.status}
                  </span>
                </td>
                <td className="py-3 px-4 text-xs">
                  {c.has_credentials ? (
                    <span className="text-emerald-700 font-medium">✓ AES Encrypted</span>
                  ) : (
                    <span className="text-gray-400">None</span>
                  )}
                </td>
                <td className="py-3 px-4 text-xs text-gray-500">
                  {c.last_success_at ? new Date(c.last_success_at).toLocaleString() : "Never"}
                </td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => handleTest(c.id)}
                    className="px-2.5 py-1 text-xs border rounded bg-white text-indigo-600 hover:bg-indigo-50"
                  >
                    Test Ping
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
