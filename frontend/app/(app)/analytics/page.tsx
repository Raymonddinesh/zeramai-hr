"use client";

import React, { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function AnalyticsDashboardPage() {
  const [selectedDept, setSelectedDept] = useState<string>("");
  const { data: dashboard, error, isLoading } = useSWR(
    `/v3/analytics/dashboard${selectedDept ? `?department=${encodeURIComponent(selectedDept)}` : ""}`,
    fetcher
  );

  return (
    <div className="space-y-6">
      {/* Header & Sub-navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Executive HR Analytics & Workforce Intelligence</h2>
          <p className="text-gray-500 text-sm mt-1">
            Real-time organizational telemetry across headcount, attrition, cost structure, and compliance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/reports"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition shadow-sm"
          >
            Report Builder
          </Link>
        </div>
      </div>

      {/* Domain Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-3">
        <Link href="/analytics" className="px-3 py-1.5 bg-indigo-50 text-indigo-700 font-semibold rounded-md text-sm">
          Overview
        </Link>
        <Link href="/analytics/workforce" className="px-3 py-1.5 hover:bg-gray-100 text-gray-600 rounded-md text-sm">
          Workforce & Headcount
        </Link>
        <Link href="/analytics/recruitment" className="px-3 py-1.5 hover:bg-gray-100 text-gray-600 rounded-md text-sm">
          Recruitment & ATS
        </Link>
        <Link href="/analytics/attendance" className="px-3 py-1.5 hover:bg-gray-100 text-gray-600 rounded-md text-sm">
          Attendance & Leave
        </Link>
        <Link href="/analytics/compensation" className="px-3 py-1.5 hover:bg-gray-100 text-gray-600 rounded-md text-sm">
          Compensation & Cost
        </Link>
        <Link href="/analytics/performance" className="px-3 py-1.5 hover:bg-gray-100 text-gray-600 rounded-md text-sm">
          Performance & LMS
        </Link>
        <Link href="/analytics/compliance" className="px-3 py-1.5 hover:bg-gray-100 text-gray-600 rounded-md text-sm">
          Statutory Compliance
        </Link>
      </div>

      {/* KPI Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Headcount</p>
          <p className="text-2xl font-extrabold text-indigo-700 mt-1">
            {isLoading ? "..." : (dashboard?.headcount?.total_employees ?? "—")}
          </p>
          <span className="text-[11px] text-emerald-600 font-medium">
            {dashboard?.headcount?.active_employees ?? 0} Active Engagements
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Attendance Rate</p>
          <p className="text-2xl font-extrabold text-blue-700 mt-1">
            {isLoading ? "..." : `${dashboard?.attendance?.attendance_rate ?? 0}%`}
          </p>
          <span className="text-[11px] text-gray-500 font-medium">
            Late arrivals: {dashboard?.attendance?.late_arrivals ?? 0}
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Workforce Cost</p>
          <p className="text-2xl font-extrabold text-amber-600 mt-1">
            {isLoading ? "..." : `₹${(dashboard?.workforce_cost?.total_workforce_cost ?? 0).toLocaleString("en-IN")}`}
          </p>
          <span className="text-[11px] text-gray-500 font-medium">Annualized projections</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Compliance Health</p>
          <p className="text-2xl font-extrabold text-purple-700 mt-1">
            {isLoading ? "..." : `${dashboard?.compliance?.compliance_score_percent ?? 100}%`}
          </p>
          <span className="text-[11px] text-purple-600 font-medium">
            Overdue items: {dashboard?.compliance?.overdue_tasks ?? 0}
          </span>
        </div>
      </div>

      {/* Grid: Department Breakdown and Funnel Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Headcount by Department</h3>
          <div className="space-y-3">
            {dashboard?.headcount?.by_department?.length > 0 ? (
              dashboard.headcount.by_department.map((dept: any) => (
                <div key={dept.name} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-gray-700">{dept.name}</span>
                    <span className="font-bold text-gray-900">{dept.count} members ({dept.percentage}%)</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="bg-indigo-600 h-2 rounded-full" style={{ width: `${dept.percentage || 10}%` }}></div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500">No departmental records found.</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Recruitment Funnel Velocity</h3>
          <div className="space-y-3">
            {dashboard?.recruitment?.funnel?.length > 0 ? (
              dashboard.recruitment.funnel.map((stage: any) => (
                <div key={stage.stage} className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg">
                  <span className="text-xs font-medium text-gray-700">{stage.stage}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-gray-900">{stage.count}</span>
                    <span className="text-[11px] px-2 py-0.5 bg-indigo-100 text-indigo-700 font-semibold rounded">
                      {stage.conversion_rate}%
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500">No active candidate funnel stages.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
