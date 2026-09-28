"use client";

import React, { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function SCIMSettingsPage() {
  const { data: config } = useSWR("/v3/integrations/scim/config", fetcher);
  const { data: events } = useSWR("/v3/integrations/scim/events?limit=25", fetcher);

  const [rotatedToken, setRotatedToken] = useState<string | null>(null);

  const handleRotate = async () => {
    if (!confirm("Rotate SCIM bearer token? External IdPs must be updated with the new token.")) return;
    try {
      const resp = await api.post("/v3/integrations/scim/config/rotate-token", {});
      setRotatedToken(resp.data.bearer_token);
      mutate("/v3/integrations/scim/config");
    } catch (err: any) {
      alert("Failed to rotate token: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SCIM 2.0 Inbound Provisioning</h1>
          <p className="text-sm text-gray-500">RFC 7643 / RFC 7644 user lifecycle and group synchronization.</p>
        </div>
        <Link href="/settings/integrations" className="text-sm text-indigo-600 hover:underline">
          ← Back to Hub
        </Link>
      </div>

      {rotatedToken && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg space-y-2">
          <span className="text-xs font-bold text-amber-900">NEW SCIM BEARER TOKEN (COPY NOW):</span>
          <div className="p-2 bg-white rounded border font-mono text-sm break-all select-all">
            {rotatedToken}
          </div>
          <button onClick={() => setRotatedToken(null)} className="text-xs text-amber-800 underline">
            Dismiss
          </button>
        </div>
      )}

      <div className="p-5 bg-white rounded-xl border shadow-sm space-y-4">
        <h2 className="text-base font-semibold text-gray-900">SCIM Endpoint Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <strong>Base URL:</strong>
            <div className="mt-1 p-2.5 bg-gray-50 rounded border font-mono">
              https://app.zeramai.com/api/v3/scim/v2
            </div>
          </div>
          <div>
            <strong>Token Status:</strong>
            <div className="mt-1 p-2.5 bg-gray-50 rounded border font-mono text-green-700">
              {config?.has_bearer_token ? "✓ Active (AES-256 Encrypted)" : "Not Configured"}
            </div>
          </div>
        </div>
        <button
          onClick={handleRotate}
          className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
        >
          Rotate Bearer Token
        </button>
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-5 space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Recent Provisioning Audit Trail</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 border-b text-gray-500 uppercase">
              <tr>
                <th className="py-2.5 px-3">Event Type</th>
                <th className="py-2.5 px-3">External Subject</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Processed At</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {events && events.length > 0 ? (
                events.map((e: any) => (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="py-2.5 px-3 font-mono font-medium">{e.event_type}</td>
                    <td className="py-2.5 px-3">{e.external_subject}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded bg-green-100 text-green-800">
                        {e.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-gray-500">{new Date(e.processed_at).toLocaleString()}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="py-4 text-center text-gray-400">
                    No provisioning events logged yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
