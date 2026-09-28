"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function IntegrationDirectoryPage() {
  const { data: providers, isLoading } = useSWR("/v3/integrations/providers", fetcher);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Integration Directory & Catalog</h1>
          <p className="text-sm text-gray-500">Pre-built connectors for identity, messaging, HR, and cloud platforms.</p>
        </div>
        <Link
          href="/settings/integrations"
          className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        >
          ← Back to Integration Hub
        </Link>
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-500 py-8 text-center">Loading integration catalog...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {providers && providers.map((p: any) => (
            <div key={p.id} className="p-5 border rounded-xl bg-white shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-medium">
                    {p.category}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">{p.provider_type}</span>
                </div>
                <h2 className="text-lg font-bold text-gray-900">{p.name}</h2>
                <p className="text-xs text-gray-600 mt-2 leading-relaxed">{p.description}</p>
              </div>
              <div className="pt-4 mt-4 border-t flex justify-end">
                <Link
                  href="/settings/integrations"
                  className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  Configure
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
