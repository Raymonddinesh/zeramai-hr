"use client";

import React from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function AttendanceAnalyticsPage() {
  const { data: att, isLoading } = useSWR("/v3/analytics/attendance", fetcher);
  const { data: leave } = useSWR("/v3/analytics/leave", fetcher);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Attendance & Leave Utilization</h2>
          <p className="text-gray-500 text-sm mt-1">Punctuality trends, absence tracking, and leave entitlement utilization.</p>
        </div>
        <Link href="/analytics" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">
          ← Back to Analytics Overview
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Attendance Rate</p>
          <p className="text-2xl font-extrabold text-blue-700 mt-1">{isLoading ? "..." : `${att?.attendance_rate ?? 0}%`}</p>
          <span className="text-[11px] text-gray-500">Present days: {att?.present_days ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Absence Rate</p>
          <p className="text-2xl font-extrabold text-red-600 mt-1">{isLoading ? "..." : `${att?.absence_rate ?? 0}%`}</p>
          <span className="text-[11px] text-gray-500">Absent days: {att?.absent_days ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Late Arrivals</p>
          <p className="text-2xl font-extrabold text-amber-600 mt-1">{isLoading ? "..." : (att?.late_arrivals ?? 0)}</p>
          <span className="text-[11px] text-amber-600 font-medium">Clock-in past threshold</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold text-gray-500 uppercase">Total Working Hours</p>
          <p className="text-2xl font-extrabold text-purple-700 mt-1">{isLoading ? "..." : (att?.working_hours ?? 0)} hrs</p>
          <span className="text-[11px] text-gray-500">Overtime: {att?.overtime_hours ?? 0} hrs</span>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
        <h3 className="font-semibold text-gray-800">Leave Distribution by Type</h3>
        <div className="space-y-3">
          {leave?.by_type?.map((item: any) => (
            <div key={item.name} className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-xs font-medium text-gray-700">{item.name}</span>
              <span className="text-xs font-bold text-gray-900">{item.count} days ({item.percentage}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
