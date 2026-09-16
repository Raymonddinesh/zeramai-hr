"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function PayrollPage() {
  const { data: components } = useSWR("/payroll/components", fetcher);
  const { data: payrollSummary } = useSWR("/analytics/payroll-summary", fetcher);
  const [computing, setComputing] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState("2026-09");
  const [lastRun, setLastRun] = useState<any>(null);

  const handleRunPayroll = async () => {
    setComputing(true);
    try {
      // 1. Create run
      const runRes = await api.post("/payroll/runs", { month: selectedMonth });
      const runId = runRes.data.id;

      // 2. Compute payroll
      const compRes = await api.post(`/payroll/runs/${runId}/compute`);

      // 3. Fetch payslips
      const slipsRes = await api.get(`/payroll/runs/${runId}/payslips`);

      setLastRun({
        ...compRes.data,
        payslips: slipsRes.data,
      });
      alert(`Payroll computed successfully for ${compRes.data.employees} employees! Total Net: ₹${compRes.data.total_net.toLocaleString()}`);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error computing payroll");
    } finally {
      setComputing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Global Payroll & Compensation Engine</h2>
          <p className="text-gray-500 text-sm">
            Phase 6: Salary structures, earnings & statutory deductions, automated batch compute & digital payslips
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-32 font-mono text-gray-800"
            placeholder="YYYY-MM"
          />
          <button
            onClick={handleRunPayroll}
            disabled={computing}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-sm transition disabled:opacity-50"
          >
            {computing ? "Computing..." : "⚡ Execute Monthly Payroll Run"}
          </button>
        </div>
      </div>

      {/* Salary Components Overview */}
      <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-200">
        <h3 className="font-semibold text-gray-800 mb-3">Statutory & Earning Components</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {(components || []).map((c: any) => (
            <div key={c.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex justify-between items-center mb-1">
                <span className="font-mono font-bold text-xs text-indigo-600">{c.code}</span>
                <span
                  className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    c.component_type === "earning"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {c.component_type}
                </span>
              </div>
              <h4 className="text-sm font-semibold text-gray-900">{c.name}</h4>
              <p className="text-xs text-gray-500 mt-1">
                {c.is_statutory ? "Statutory compliance (PF/ESI)" : "Taxable standard component"}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Computed Run Results & Payslips */}
      {lastRun && (
        <div className="bg-white rounded-xl shadow-sm p-6 border border-emerald-200 space-y-4">
          <div className="flex justify-between items-center border-b pb-3">
            <div>
              <h3 className="font-bold text-gray-900 text-lg">Batch Payroll Summary ({selectedMonth})</h3>
              <p className="text-xs text-emerald-700 font-medium">Status: {lastRun.status?.toUpperCase()}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Total Net Disbursement</p>
              <p className="text-2xl font-bold text-emerald-700">₹{lastRun.total_net?.toLocaleString()}</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase border-b">
                <tr>
                  <th className="px-4 py-2.5">Person ID</th>
                  <th className="px-4 py-2.5">Month</th>
                  <th className="px-4 py-2.5">Gross Salary</th>
                  <th className="px-4 py-2.5">Deductions</th>
                  <th className="px-4 py-2.5">Net Payout</th>
                </tr>
              </thead>
              <tbody className="divide-y text-gray-700">
                {(lastRun.payslips || []).map((p: any) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono text-gray-600 truncate max-w-[120px]">{p.person_id}</td>
                    <td className="px-4 py-2.5 font-mono">{p.month}</td>
                    <td className="px-4 py-2.5 font-semibold text-gray-900">₹{Number(p.gross_salary).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-red-600">₹{Number(p.total_deductions).toLocaleString()}</td>
                    <td className="px-4 py-2.5 font-bold text-emerald-700">₹{Number(p.net_salary).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Historical Runs */}
      <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-200">
        <h3 className="font-semibold text-gray-800 mb-3">Historical Payroll Runs</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase border-b">
              <tr>
                <th className="px-4 py-2.5">Payroll Month</th>
                <th className="px-4 py-2.5">Headcount</th>
                <th className="px-4 py-2.5">Total Gross</th>
                <th className="px-4 py-2.5">Total Net</th>
                <th className="px-4 py-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y text-gray-700">
              {(payrollSummary || []).map((r: any, idx: number) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono font-bold text-gray-900">{r.month}</td>
                  <td className="px-4 py-2.5">{r.employees} Employees</td>
                  <td className="px-4 py-2.5">₹{Number(r.total_gross).toLocaleString()}</td>
                  <td className="px-4 py-2.5 font-semibold text-emerald-700">₹{Number(r.total_net).toLocaleString()}</td>
                  <td className="px-4 py-2.5">
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-medium uppercase">
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
              {(!payrollSummary || payrollSummary.length === 0) && (
                <tr>
                  <td colSpan={5} className="text-center py-6 text-gray-400">
                    No completed payroll runs found. Click "Execute Monthly Payroll Run" above to compute.
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
