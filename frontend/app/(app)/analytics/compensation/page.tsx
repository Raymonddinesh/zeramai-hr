"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function CompensationAnalyticsPage() {
  const { data: comp, error, isLoading } = useSWR("/v3/analytics/compensation?min_threshold=1", fetcher);
  const { data: cost } = useSWR("/v3/analytics/workforce-cost", fetcher);

  if (error?.response?.status === 403) {
    return (
      <div className="p-8 bg-red-50 border border-red-200 rounded-xl text-center space-y-3">
        <h3 className="text-lg font-bold text-red-700">Access Restricted</h3>
        <p className="text-sm text-red-600">You do not have authorized RBAC permissions to view company compensation analytics.</p>
        <Link href="/analytics" className="inline-block px-4 py-2 bg-red-700 text-white rounded text-sm font-medium">
          Return to Overview
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Compensation & Workforce Cost Telemetry</h2>
          <p className="text-gray-500 text-sm mt-1">Salary distributions, fixed vs. variable components, and employer overheads.</p>
        </div>
        <Link href="/analytics" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
          ← Back to Analytics Overview
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Total Payroll Cost</p>
          <p className="text-2xl font-extrabold text-indigo-700 mt-1">
            {isLoading ? "..." : comp?.is_redacted ? "[REDACTED]" : `₹${(comp?.total_payroll_cost ?? 0).toLocaleString("en-IN")}`}
          </p>
          <span className="text-[11px] text-gray-500">Sample: {comp?.sample_size ?? 0} employees</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Fixed Compensation</p>
          <p className="text-2xl font-extrabold text-blue-700 mt-1">
            {isLoading ? "..." : comp?.is_redacted ? "[REDACTED]" : `₹${(comp?.fixed_compensation ?? 0).toLocaleString("en-IN")}`}
          </p>
          <span className="text-[11px] text-gray-500">Base salary structure</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Employer Statutory</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">
            {isLoading ? "..." : `₹${(cost?.employer_statutory_cost ?? 0).toLocaleString("en-IN")}`}
          </p>
          <span className="text-[11px] text-emerald-600 font-medium">PF, ESI & statutory dues</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Total Workforce Cost</p>
          <p className="text-2xl font-extrabold text-amber-600 mt-1">
            {isLoading ? "..." : `₹${(cost?.total_workforce_cost ?? 0).toLocaleString("en-IN")}`}
          </p>
          <span className="text-[11px] text-gray-500">Including overhead & benefits</span>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
        <h3 className="font-semibold text-gray-800">Salary Band Distribution</h3>
        <div className="space-y-3">
          {comp?.salary_distribution?.map((item: any) => (
            <div key={item.name} className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-xs font-medium text-gray-700">{item.name}</span>
              <span className="text-xs font-bold text-gray-900">{item.count} ({item.percentage}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
