"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function ComplianceCalendarPage() {
  const { data: events, mutate } = useSWR("/api/v3/compliance-calendar", fetcher);
  const [filterType, setFilterType] = useState<string>("all");

  const filteredEvents = events?.filter((e: any) =>
    filterType === "all" ? true : e.compliance_type === filterType
  );

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">HR & Statutory Compliance Calendar</h1>
          <p className="text-gray-500 text-sm mt-1">
            Module 12: Automated tracking of EPF, ESIC, PT, TDS, and statutory return filing deadlines.
          </p>
        </div>

        <div className="flex space-x-2">
          {["all", "statutory", "payroll", "hr", "policy"].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase transition ${
                filterType === type
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Event / Obligation</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Authority</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Period</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Due Date</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredEvents && filteredEvents.length > 0 ? (
                filteredEvents.map((evt: any) => (
                  <tr key={evt.id}>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-gray-900 block">{evt.title}</span>
                      {evt.description && <span className="text-xs text-gray-500">{evt.description}</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 uppercase">
                        {evt.compliance_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 uppercase text-gray-600">{evt.authority || "Internal"}</td>
                    <td className="px-4 py-3 text-gray-600">{evt.period || "Monthly"}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{evt.due_date}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                          evt.status === "completed"
                            ? "bg-green-100 text-green-800"
                            : evt.status === "overdue"
                            ? "bg-red-100 text-red-800"
                            : "bg-amber-100 text-amber-800"
                        } uppercase`}
                      >
                        {evt.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    No compliance events scheduled for the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
