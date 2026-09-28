"use client";

import React, { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function WebhooksPage() {
  const { data: webhooks, isLoading } = useSWR("/v3/integrations/webhooks", fetcher);

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState("employee.onboarded, employee.offboarded");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v3/integrations/webhooks", {
        name,
        url,
        subscribed_events: events.split(",").map((s) => s.trim()),
      });
      setName("");
      setUrl("");
      mutate("/v3/integrations/webhooks");
    } catch (err: any) {
      alert("Failed to register webhook: " + (err.response?.data?.detail || err.message));
    }
  };

  const handlePing = async (id: string) => {
    try {
      const resp = await api.post(`/v3/integrations/webhooks/${id}/test`, {});
      alert(`Ping result: ${resp.data.message}`);
      mutate("/v3/integrations/webhooks");
    } catch (err: any) {
      alert("Ping failed: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhook Subscriptions</h1>
          <p className="text-sm text-gray-500">Real-time outbound webhooks signed with HMAC-SHA256.</p>
        </div>
        <Link href="/settings/integrations" className="text-sm text-indigo-600 hover:underline">
          ← Back to Hub
        </Link>
      </div>

      <form onSubmit={handleCreate} className="p-5 bg-white rounded-xl border shadow-sm space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Register Endpoint</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            required
            placeholder="Endpoint Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="p-2 border rounded text-xs bg-white"
          />
          <input
            type="url"
            required
            placeholder="https://your-domain.com/webhook"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="p-2 border rounded text-xs bg-white"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
        >
          Save Endpoint
        </button>
      </form>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-gray-50 border-b text-gray-500 uppercase">
            <tr>
              <th className="py-3 px-4">Name</th>
              <th className="py-3 px-4">Target URL</th>
              <th className="py-3 px-4">Events</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {webhooks && webhooks.map((w: any) => (
              <tr key={w.id} className="hover:bg-gray-50">
                <td className="py-3 px-4 font-semibold text-gray-900">{w.name}</td>
                <td className="py-3 px-4 font-mono text-gray-600">{w.url}</td>
                <td className="py-3 px-4">{w.subscribed_events?.join(", ")}</td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => handlePing(w.id)}
                    className="px-2.5 py-1 border rounded bg-white text-indigo-600 hover:bg-indigo-50"
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
