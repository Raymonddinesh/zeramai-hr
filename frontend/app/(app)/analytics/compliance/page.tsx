"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function ComplianceAnalyticsPage() {
  const { data: comp, isLoading } = useSWR("/v3/analytics/compliance", fetcher);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Statutory Compliance & Task Telemetry</h2>
          <p className="text-gray-500 text-sm mt-1">EPF, ESI, PT, and TDS filing health and statutory calendar completion.</p>
        </div>
        <Link href="/analytics" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
          ← Back to Analytics Overview
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Compliance Health Score</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">{isLoading ? "..." : `${comp?.compliance_score_percent ?? 100}%`}</p>
          <span className="text-[11px] text-emerald-600 font-medium">On-time completion rate</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Total Compliance Tasks</p>
          <p className="text-2xl font-extrabold text-indigo-700 mt-1">{isLoading ? "..." : (comp?.total_tasks ?? 0)}</p>
          <span className="text-[11px] text-gray-500">Completed: {comp?.completed_tasks ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Overdue Items</p>
          <p className="text-2xl font-extrabold text-red-600 mt-1">{isLoading ? "..." : (comp?.overdue_tasks ?? 0)}</p>
          <span className="text-[11px] text-red-600 font-medium">Requires immediate escalation</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Tax Declarations Verified</p>
          <p className="text-2xl font-extrabold text-purple-700 mt-1">{isLoading ? "..." : `${comp?.tax_declarations_completion_percent ?? 100}%`}</p>
          <span className="text-[11px] text-gray-500">Annual IT declarations</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Statutory Return Filings Status</h3>
          <div className="space-y-3">
            {comp?.statutory_filings_by_status?.length > 0 ? (
              comp.statutory_filings_by_status.map((item: any) => (
                <div key={item.name} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="text-xs font-medium text-gray-700">{item.name}</span>
                  <span className="text-xs font-bold text-gray-900">{item.count} filings</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500">No statutory filings recorded.</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Challan Payments Reconciliation</h3>
          <div className="space-y-3">
            {comp?.statutory_payments_by_status?.length > 0 ? (
              comp.statutory_payments_by_status.map((item: any) => (
                <div key={item.name} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="text-xs font-medium text-gray-700">{item.name}</span>
                  <span className="text-xs font-bold text-gray-900">{item.count} payments</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500">No payment challans recorded.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
