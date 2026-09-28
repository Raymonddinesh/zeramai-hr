"use client";

import React from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function IntegrationLogsPage() {
  const { data: logs, isLoading: logsLoading } = useSWR("/v3/integrations/logs?limit=50", fetcher);
  const { data: outbox, isLoading: outboxLoading } = useSWR("/v3/integrations/outbox?limit=50", fetcher);

  const handleFlushOutbox = async () => {
    try {
      const resp = await api.post("/v3/integrations/outbox/process", {});
      alert(`Outbox processed: ${resp.data.processed_count} events dispatched.`);
      mutate("/v3/integrations/outbox?limit=50");
      mutate("/v3/integrations/logs?limit=50");
    } catch (err: any) {
      alert("Failed to process outbox: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Integration Logs & Outbox Telemetry</h1>
          <p className="text-sm text-gray-500">Live operational monitoring of outbound events, webhooks, and sync tasks.</p>
        </div>
        <div className="flex gap-4 items-center">
          <button
            onClick={handleFlushOutbox}
            className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
          >
            Flush Outbox
          </button>
          <Link href="/settings/integrations" className="text-sm text-indigo-600 hover:underline">
            ← Back to Hub
          </Link>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded-xl border shadow-sm p-5 space-y-3">
          <h2 className="text-base font-semibold text-gray-900">Transactional Outbox Queue</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 border-b text-gray-500 uppercase">
                <tr>
                  <th className="py-2.5 px-3">Event</th>
                  <th className="py-2.5 px-3">Aggregate</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Retries</th>
                  <th className="py-2.5 px-3">Available At</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {outbox && outbox.length > 0 ? (
                  outbox.map((e: any) => (
                    <tr key={e.id} className="hover:bg-gray-50">
                      <td className="py-2.5 px-3 font-mono font-medium">{e.event_type}</td>
                      <td className="py-2.5 px-3">{e.aggregate_type}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          e.status === "PROCESSED" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                        }`}>
                          {e.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">{e.retry_count}</td>
                      <td className="py-2.5 px-3 text-gray-500">{new Date(e.available_at).toLocaleTimeString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-gray-400">
                      Outbox queue is empty.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-xl border shadow-sm p-5 space-y-3">
          <h2 className="text-base font-semibold text-gray-900">Execution Telemetry History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 border-b text-gray-500 uppercase">
                <tr>
                  <th className="py-2.5 px-3">Event Type</th>
                  <th className="py-2.5 px-3">Direction</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Latency</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs && logs.length > 0 ? (
                  logs.map((l: any) => (
                    <tr key={l.id} className="hover:bg-gray-50">
                      <td className="py-2.5 px-3 font-mono font-medium">{l.event_type}</td>
                      <td className="py-2.5 px-3">{l.direction}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          l.status === "SUCCESS" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                        }`}>
                          {l.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">{l.duration_ms}ms</td>
                      <td className="py-2.5 px-3 text-gray-500">{new Date(l.created_at).toLocaleTimeString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-gray-400">
                      No execution logs recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
