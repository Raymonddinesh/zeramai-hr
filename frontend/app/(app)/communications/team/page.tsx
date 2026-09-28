"use client";

import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function ManagerTeamCommunicationsPage() {
  const { data: teamSummary, error, isLoading } = useSWR("/api/v3/communications/team", fetcher);

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500">
        <p className="text-xl animate-pulse">⏳</p>
        <p className="text-xs mt-2">Loading team communications metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-sm">
        <p className="font-bold">Manager Scope Access</p>
        <p className="text-xs mt-1">
          {error.response?.data?.detail || "You do not have direct reports or manager permissions configured."}
        </p>
      </div>
    );
  }

  const readRate = teamSummary?.team_read_rate_pct ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-2xl">👥</span>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Manager Team Communications
          </h1>
        </div>
        <p className="text-slate-500 text-xs mt-1">
          Monitor announcement engagement, compliance acknowledgements, and read rates strictly for your direct reporting line.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Direct Reports</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-2">{teamSummary?.team_size || 0}</p>
          <p className="text-[11px] text-slate-400 mt-1">Active team engagements</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Broadcasts</p>
          <p className="text-2xl font-extrabold text-indigo-600 mt-2">{teamSummary?.announcements_count || 0}</p>
          <p className="text-[11px] text-slate-400 mt-1">Targeted to your organization</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Team Read Rate</p>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-extrabold text-slate-900">{readRate}%</span>
            <span className="text-xs text-slate-500">
              ({teamSummary?.team_read_count || 0} reads)
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
            <div
              className={`h-1.5 rounded-full ${
                readRate >= 80 ? "bg-emerald-500" : readRate >= 50 ? "bg-indigo-500" : "bg-amber-500"
              }`}
              style={{ width: `${Math.min(100, readRate)}%` }}
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Acknowledgements</p>
          <p className="text-2xl font-extrabold text-purple-600 mt-2">
            {teamSummary?.team_acknowledgement_count || 0}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Non-policy compliance notices</p>
        </div>
      </div>

      {/* Compliance Overview Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">Team Engagement Overview</h2>
          <span className="text-xs bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-md font-semibold">
            Aggregated Telemetry
          </span>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 leading-relaxed">
          <p className="font-semibold text-slate-800 mb-1">🔒 Privacy-Preserving Governance Standard</p>
          In accordance with enterprise data minimization guidelines, individual employee reading timestamps and browsing patterns are not exposed to managers. Aggregate progress rates reflect team compliance without compromising personal telemetry.
        </div>

        <div className="pt-2">
          <p className="text-xs text-slate-500">
            For critical policy sign-offs (e.g. Code of Conduct, Anti-Bribery), refer to the Module 8 HR Policy System.
          </p>
        </div>
      </div>
    </div>
  );
}
