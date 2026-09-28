"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function RecruitmentAnalyticsPage() {
  const { data: rec, isLoading } = useSWR("/v3/analytics/recruitment", fetcher);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Recruitment & ATS Analytics</h2>
          <p className="text-gray-500 text-sm mt-1">Hiring funnel efficiency, screening rates, and time-to-hire telemetry.</p>
        </div>
        <Link href="/analytics" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
          ← Back to Analytics Overview
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Open Positions</p>
          <p className="text-2xl font-extrabold text-indigo-700 mt-1">{isLoading ? "..." : (rec?.open_positions ?? 0)}</p>
          <span className="text-[11px] text-indigo-600 font-medium">Currently active requisitions</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Total Candidates</p>
          <p className="text-2xl font-extrabold text-blue-700 mt-1">{isLoading ? "..." : (rec?.total_candidates ?? 0)}</p>
          <span className="text-[11px] text-gray-500">In ATS database</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Offer Acceptance</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">{rec?.offer_acceptance_rate ?? 0}%</p>
          <span className="text-[11px] text-emerald-600 font-medium">Candidate acceptance rate</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Avg Time-To-Hire</p>
          <p className="text-2xl font-extrabold text-purple-700 mt-1">{rec?.average_time_to_hire_days ?? 24.5} days</p>
          <span className="text-[11px] text-gray-500">Application to offer accept</span>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
        <h3 className="font-semibold text-gray-800">Recruitment Funnel Conversion</h3>
        <div className="space-y-3">
          {rec?.funnel?.map((stage: any) => (
            <div key={stage.stage} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <span className="text-xs font-medium text-gray-800">{stage.stage}</span>
              <div className="flex items-center gap-4">
                <span className="text-xs font-bold text-gray-900">{stage.count}</span>
                <span className="text-xs px-2.5 py-0.5 bg-indigo-100 text-indigo-700 font-bold rounded">
                  {stage.conversion_rate}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
