"use client";

import React, { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function WorkforceAnalyticsPage() {
  const [deptFilter, setDeptFilter] = useState("");
  const { data: hc, isLoading: hcLoading } = useSWR(
    `/v3/analytics/headcount${deptFilter ? `?department=${encodeURIComponent(deptFilter)}` : ""}`,
    fetcher
  );
  const { data: att } = useSWR("/v3/analytics/attrition", fetcher);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Workforce & Headcount Intelligence</h2>
          <p className="text-gray-500 text-sm mt-1">Detailed demographic, tenure, and organizational headcount telemetry.</p>
        </div>
        <Link href="/analytics" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
          ← Back to Analytics Overview
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Total Headcount</p>
          <p className="text-2xl font-extrabold text-indigo-700 mt-1">{hcLoading ? "..." : (hc?.total_employees ?? "—")}</p>
          <span className="text-[11px] text-gray-500">Active: {hc?.active_employees ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">New Hires (90 Days)</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">{hcLoading ? "..." : (hc?.new_hires ?? 0)}</p>
          <span className="text-[11px] text-emerald-600 font-medium">Recent additions</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Annualized Turnover</p>
          <p className="text-2xl font-extrabold text-amber-600 mt-1">{att?.turnover_rate ?? 0}%</p>
          <span className="text-[11px] text-gray-500">Resignation: {att?.resignation_rate ?? 0}%</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Average Tenure</p>
          <p className="text-2xl font-extrabold text-purple-700 mt-1">{att?.average_tenure_months ?? 12} mo</p>
          <span className="text-[11px] text-purple-600 font-medium">Across all active contracts</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Employment Type Distribution</h3>
          <div className="space-y-3">
            {hc?.by_employment_type?.map((item: any) => (
              <div key={item.name} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                <span className="text-xs font-medium text-gray-700">{item.name}</span>
                <span className="text-xs font-bold text-gray-900">{item.count} ({item.percentage}%)</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Tenure Band Distribution</h3>
          <div className="space-y-3">
            {att?.by_tenure_band?.map((item: any) => (
              <div key={item.name} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                <span className="text-xs font-medium text-gray-700">{item.name}</span>
                <span className="text-xs font-bold text-gray-900">{item.count} ({item.percentage}%)</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
