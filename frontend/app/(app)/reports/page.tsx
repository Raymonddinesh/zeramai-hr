"use client";

import React, { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function ReportsPage() {
  const { data: reports, isLoading: reportsLoading } = useSWR("/v3/reports", fetcher);
  const { data: scheduled, isLoading: scheduledLoading } = useSWR("/v3/reports/scheduled", fetcher);

  const [activeTab, setActiveTab] = useState<"reports" | "scheduled" | "create">("reports");
  const [reportName, setReportName] = useState("");
  const [reportType, setReportType] = useState("WORKFORCE");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState("PUBLIC");
  const [minThreshold, setMinThreshold] = useState(3);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [executionMessage, setExecutionMessage] = useState<string | null>(null);

  const handleCreateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v3/reports", {
        name: reportName,
        report_type: reportType,
        description,
        visibility,
        min_aggregation_threshold: minThreshold,
      });
      setReportName("");
      setDescription("");
      setActiveTab("reports");
      mutate("/v3/reports");
      setExecutionMessage("Report definition created successfully.");
    } catch (err: any) {
      alert("Failed to create report: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleExecuteReport = async (id: string) => {
    setExecutingId(id);
    try {
      const resp = await api.post(`/v3/reports/${id}/execute`, {});
      setExecutionMessage(`Execution successful! Row count: ${resp.data.row_count} in ${resp.data.execution_time_ms}ms.`);
    } catch (err: any) {
      alert("Execution failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setExecutingId(null);
    }
  };

  const handleExportCSV = async (id: string, name: string) => {
    try {
      const resp = await api.post(`/v3/reports/${id}/export?format=CSV`, {}, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${name.toLowerCase().replace(/\s+/g, "_")}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      alert("Export failed: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Enterprise Report Builder & Schedules</h2>
          <p className="text-gray-500 text-sm mt-1">Configurable report definitions, automated schedules, and compliance CSV exports.</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/analytics" className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium">
            ← Analytics Dashboard
          </Link>
          <button
            onClick={() => setActiveTab("create")}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium shadow-sm"
          >
            + New Report
          </button>
        </div>
      </div>

      {executionMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-medium flex justify-between items-center">
          <span>{executionMessage}</span>
          <button onClick={() => setExecutionMessage(null)} className="text-emerald-600 hover:text-emerald-900">✕</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        <button
          onClick={() => setActiveTab("reports")}
          className={`px-3 py-1.5 text-sm font-semibold rounded-md ${
            activeTab === "reports" ? "bg-indigo-50 text-indigo-700" : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          Saved Reports ({reports?.length ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("scheduled")}
          className={`px-3 py-1.5 text-sm font-semibold rounded-md ${
            activeTab === "scheduled" ? "bg-indigo-50 text-indigo-700" : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          Scheduled Runs ({scheduled?.length ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("create")}
          className={`px-3 py-1.5 text-sm font-semibold rounded-md ${
            activeTab === "create" ? "bg-indigo-50 text-indigo-700" : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          Create Definition
        </button>
      </div>

      {/* Tab: Saved Reports */}
      {activeTab === "reports" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Report Name</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Domain</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Visibility</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Min Threshold</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports?.map((r: any) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-bold text-gray-900">{r.name}</p>
                    <p className="text-gray-500 text-[11px]">{r.description || "No description"}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 font-semibold rounded">{r.report_type}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-700 font-medium rounded">{r.visibility}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.min_aggregation_threshold} members</td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      onClick={() => handleExecuteReport(r.id)}
                      disabled={executingId === r.id}
                      className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded font-medium disabled:opacity-50"
                    >
                      {executingId === r.id ? "Running..." : "Execute"}
                    </button>
                    <button
                      onClick={() => handleExportCSV(r.id, r.name)}
                      className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded font-medium"
                    >
                      Export CSV
                    </button>
                  </td>
                </tr>
              ))}
              {reports?.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No custom report definitions created yet. Click "+ New Report" to create one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Scheduled Runs */}
      {activeTab === "scheduled" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Schedule ID</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Frequency</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Format</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Recipients</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {scheduled?.map((s: any) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-[11px] text-gray-500">{s.id.slice(0, 8)}...</td>
                  <td className="px-4 py-3 font-bold text-gray-900">{s.frequency}</td>
                  <td className="px-4 py-3 font-semibold text-indigo-600">{s.format}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded font-semibold ${s.status === "ACTIVE" ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{s.recipients?.join(", ")}</td>
                </tr>
              ))}
              {scheduled?.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No recurring schedules configured yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Create Definition */}
      {activeTab === "create" && (
        <form onSubmit={handleCreateReport} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4 max-w-xl">
          <h3 className="text-base font-bold text-gray-900">Define New Analytics Report</h3>
          
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Report Name</label>
            <input
              type="text"
              required
              value={reportName}
              onChange={(e) => setReportName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="e.g. Monthly Headcount & Attrition Snapshot"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Domain Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs"
              >
                <option value="WORKFORCE">WORKFORCE</option>
                <option value="ATTENDANCE">ATTENDANCE</option>
                <option value="RECRUITMENT">RECRUITMENT</option>
                <option value="COMPENSATION">COMPENSATION</option>
                <option value="PERFORMANCE">PERFORMANCE</option>
                <option value="COMPLIANCE">COMPLIANCE</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Visibility</label>
              <select
                value={visibility}
                onChange={(e) => setVisibility(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs"
              >
                <option value="PUBLIC">PUBLIC</option>
                <option value="PRIVATE">PRIVATE</option>
                <option value="ROLE_BASED">ROLE_BASED</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Privacy Aggregation Threshold</label>
            <input
              type="number"
              min={1}
              max={50}
              value={minThreshold}
              onChange={(e) => setMinThreshold(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs"
            />
            <p className="text-[11px] text-gray-500 mt-1">Samples smaller than this size will redact sensitive metrics.</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs"
              placeholder="Operational rationale and intended audience..."
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setActiveTab("reports")}
              className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium shadow-sm"
            >
              Save Report Definition
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
