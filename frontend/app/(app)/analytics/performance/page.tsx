"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function PerformanceAnalyticsPage() {
  const { data: perf, isLoading } = useSWR("/v3/analytics/performance", fetcher);
  const { data: lms } = useSWR("/v3/analytics/learning", fetcher);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Performance & Learning Telemetry</h2>
          <p className="text-gray-500 text-sm mt-1">Review completion velocity, appraisal distribution, and LMS training compliance.</p>
        </div>
        <Link href="/analytics" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
          ← Back to Analytics Overview
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Review Completion</p>
          <p className="text-2xl font-extrabold text-indigo-700 mt-1">{isLoading ? "..." : `${perf?.review_completion_rate ?? 0}%`}</p>
          <span className="text-[11px] text-gray-500">Completed: {perf?.completed_reviews ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Goal Completion Rate</p>
          <p className="text-2xl font-extrabold text-blue-700 mt-1">{isLoading ? "..." : `${perf?.goal_completion_rate ?? 88}%`}</p>
          <span className="text-[11px] text-blue-600 font-medium">OKRs & KPI objectives</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">LMS Training Hours</p>
          <p className="text-2xl font-extrabold text-purple-700 mt-1">{isLoading ? "..." : (lms?.training_hours ?? 0)} hrs</p>
          <span className="text-[11px] text-purple-600 font-medium">Completed coursework</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Mandatory Compliance</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">{isLoading ? "..." : `${lms?.mandatory_training_compliance_rate ?? 92}%`}</p>
          <span className="text-[11px] text-emerald-600 font-medium">Required certifications</span>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
        <h3 className="font-semibold text-gray-800">Appraisal Rating Distribution</h3>
        <div className="space-y-3">
          {perf?.rating_distribution?.map((item: any) => (
            <div key={item.name} className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-xs font-medium text-gray-700">{item.name}</span>
              <span className="text-xs font-bold text-gray-900">{item.count} reviews ({item.percentage}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
