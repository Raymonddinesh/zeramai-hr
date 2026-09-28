"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

type TabType = "calendars" | "paygroups" | "components" | "fx" | "adjustments" | "reconciliations";

export default function GlobalPayrollAdminPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>("calendars");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // SWR queries
  const { data: calendars, mutate: mutateCalendars } = useSWR("/api/v3/global-payroll/calendars", fetcher);
  const { data: payGroups, mutate: mutatePayGroups } = useSWR("/api/v3/global-payroll/pay-groups", fetcher);
  const { data: components, mutate: mutateComponents } = useSWR("/api/v3/global-payroll/components", fetcher);
  const { data: fxRates, mutate: mutateFxRates } = useSWR("/api/v3/global-payroll/exchange-rates", fetcher);
  const { data: adjustments, mutate: mutateAdjustments } = useSWR("/api/v3/global-payroll/adjustments", fetcher);
  const { data: reconciliations, mutate: mutateReconciliations } = useSWR("/api/v3/global-payroll/reconciliations", fetcher);

  // Workflow actions for Calendars
  const handleCalculate = async (calendarId: string) => {
    setActionLoading(calendarId);
    setStatusMsg(null);
    try {
      const res = await api.post(`/api/v3/global-payroll/calendars/${calendarId}/calculate`);
      setStatusMsg(`Calculated ${res.data.count} payroll results successfully.`);
      mutateCalendars();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Calculation failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleValidate = async (calendarId: string) => {
    setActionLoading(calendarId);
    setStatusMsg(null);
    try {
      await api.post(`/api/v3/global-payroll/calendars/${calendarId}/validate`);
      setStatusMsg("Payroll run validated successfully.");
      mutateCalendars();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Validation failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleApprove = async (calendarId: string) => {
    setActionLoading(calendarId);
    setStatusMsg(null);
    try {
      await api.post(`/api/v3/global-payroll/calendars/${calendarId}/approve`);
      setStatusMsg("Payroll run approved successfully.");
      mutateCalendars();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Approval failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleFinalize = async (calendarId: string) => {
    setActionLoading(calendarId);
    setStatusMsg(null);
    try {
      const res = await api.post(`/api/v3/global-payroll/calendars/${calendarId}/finalize`);
      setStatusMsg(`Finalized payroll and generated ${res.data.payslips_generated} payslips.`);
      mutateCalendars();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Finalization failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReconcile = async (calendarId: string) => {
    setActionLoading(calendarId);
    setStatusMsg(null);
    try {
      const res = await api.post(`/api/v3/global-payroll/calendars/${calendarId}/reconcile`);
      setStatusMsg(`Reconciliation status: ${res.data.status} (Variance: ${res.data.variance})`);
      mutateReconciliations();
      mutateCalendars();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Reconciliation failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleProcessAdjustment = async (adjId: string) => {
    setActionLoading(adjId);
    setStatusMsg(null);
    try {
      await api.post(`/api/v3/global-payroll/adjustments/${adjId}/process`);
      setStatusMsg("Adjustment processed and committed to target calendar.");
      mutateAdjustments();
      mutateCalendars();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Processing adjustment failed");
    } finally {
      setActionLoading(null);
    }
  };

  if (user && !["super_admin", "hr_admin", "finance"].includes(user.role)) {
    return (
      <div className="p-8 text-center bg-rose-50 border border-rose-200 rounded-xl text-rose-800">
        <h2 className="text-lg font-bold">Access Restricted</h2>
        <p className="text-sm mt-1">You do not have administrative privileges to manage global payroll.</p>
        <Link href="/global-payroll" className="mt-4 inline-block text-xs font-semibold text-rose-900 underline">
          Return to Global Payroll Hub
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🗺️</span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Global Payroll Administration
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Configure multi-country calendars, pay groups, statutory rules, FX snapshots & reconciliation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/global-payroll"
            className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
          >
            ← Global Hub
          </Link>
        </div>
      </div>

      {statusMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium rounded-xl flex items-center justify-between">
          <span>✓ {statusMsg}</span>
          <button onClick={() => setStatusMsg(null)} className="text-emerald-600 hover:text-emerald-900">✕</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto gap-2">
        <button
          onClick={() => setActiveTab("calendars")}
          className={`pb-3 px-4 text-xs font-bold transition whitespace-nowrap border-b-2 ${
            activeTab === "calendars"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          📅 Payroll Calendars & Execution ({calendars?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab("paygroups")}
          className={`pb-3 px-4 text-xs font-bold transition whitespace-nowrap border-b-2 ${
            activeTab === "paygroups"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          🏢 Pay Groups ({payGroups?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab("components")}
          className={`pb-3 px-4 text-xs font-bold transition whitespace-nowrap border-b-2 ${
            activeTab === "components"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          📦 Pay Components ({components?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab("fx")}
          className={`pb-3 px-4 text-xs font-bold transition whitespace-nowrap border-b-2 ${
            activeTab === "fx"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          💱 FX Snapshots ({fxRates?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab("adjustments")}
          className={`pb-3 px-4 text-xs font-bold transition whitespace-nowrap border-b-2 ${
            activeTab === "adjustments"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          🔄 Retro Adjustments ({adjustments?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab("reconciliations")}
          className={`pb-3 px-4 text-xs font-bold transition whitespace-nowrap border-b-2 ${
            activeTab === "reconciliations"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          ⚖️ Reconciliations ({reconciliations?.length || 0})
        </button>
      </div>

      {/* Tab: Calendars */}
      {activeTab === "calendars" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
          <div className="px-6 py-4 bg-slate-50 flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Multi-Country Payroll Cycles
              </h3>
              <p className="text-xs text-slate-500">
                Execute end-to-end gross-to-net calculations, validations, approvals, and immutable finalizations.
              </p>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {calendars?.map((cal: any) => (
              <div key={cal.id} className="p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{cal.name}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        cal.status === "FINALIZED"
                          ? "bg-slate-900 text-white"
                          : cal.status === "APPROVED"
                          ? "bg-emerald-100 text-emerald-800"
                          : cal.status === "VALIDATED"
                          ? "bg-blue-100 text-blue-800"
                          : cal.status === "CALCULATED"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {cal.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Cycle: <strong className="text-slate-700">{cal.period_start}</strong> to{" "}
                    <strong className="text-slate-700">{cal.period_end}</strong> | Cut-Off: {cal.cut_off_date} | Pay Date: {cal.payment_date}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    Pay Group: {cal.pay_group?.name || "Global Group"} ({cal.pay_group?.currency})
                  </p>
                </div>

                {/* Workflow Actions */}
                <div className="flex flex-wrap items-center gap-2">
                  {cal.status !== "FINALIZED" && (
                    <>
                      <button
                        disabled={actionLoading === cal.id}
                        onClick={() => handleCalculate(cal.id)}
                        className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-lg transition disabled:opacity-50"
                      >
                        {actionLoading === cal.id ? "Processing..." : "⚡ Calculate"}
                      </button>

                      {["CALCULATED", "VALIDATED", "APPROVED"].includes(cal.status) && (
                        <button
                          disabled={actionLoading === cal.id}
                          onClick={() => handleValidate(cal.id)}
                          className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold rounded-lg transition disabled:opacity-50"
                        >
                          ✓ Validate
                        </button>
                      )}

                      {["VALIDATED", "APPROVED"].includes(cal.status) && (
                        <button
                          disabled={actionLoading === cal.id}
                          onClick={() => handleApprove(cal.id)}
                          className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-lg transition disabled:opacity-50"
                        >
                          ★ Approve
                        </button>
                      )}

                      {cal.status === "APPROVED" && (
                        <button
                          disabled={actionLoading === cal.id}
                          onClick={() => handleFinalize(cal.id)}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
                        >
                          🔒 Finalize & Lock
                        </button>
                      )}
                    </>
                  )}

                  <button
                    disabled={actionLoading === cal.id}
                    onClick={() => handleReconcile(cal.id)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition disabled:opacity-50"
                  >
                    ⚖️ Reconcile
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Pay Groups */}
      {activeTab === "paygroups" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Multi-Entity Pay Groups
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {payGroups?.map((pg: any) => (
              <div key={pg.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                <div className="flex justify-between items-start">
                  <span className="font-bold text-slate-900 text-sm">{pg.name}</span>
                  <span className="font-mono text-xs font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">
                    {pg.currency}
                  </span>
                </div>
                <div className="text-xs text-slate-500 space-y-1">
                  <p>Code: <span className="font-mono text-slate-700">{pg.code}</span></p>
                  <p>Frequency: <strong className="text-slate-700">{pg.pay_frequency}</strong></p>
                  <p>Country: <strong className="text-slate-700">{pg.configuration?.country?.country_name || "Global"}</strong></p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Pay Components */}
      {activeTab === "components" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Global Pay Components Catalog
          </h3>
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100 text-xs">
            {components?.map((c: any) => (
              <div key={c.id} className="p-3 flex justify-between items-center">
                <div>
                  <span className="font-semibold text-slate-800">{c.name}</span>
                  <span className="ml-2 font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                    {c.code}
                  </span>
                  <span className="ml-2 text-[10px] bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-bold">
                    {c.component_type}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-500">
                    Taxable: {c.is_taxable ? "Yes" : "No"} | Statutory: {c.is_statutory ? "Yes" : "No"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: FX Snapshots */}
      {activeTab === "fx" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Multi-Currency Exchange Rate Audit Snapshots
          </h3>
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100 text-xs">
            {fxRates?.map((fx: any) => (
              <div key={fx.id} className="p-3 flex justify-between items-center">
                <div>
                  <span className="font-mono font-bold text-slate-900">
                    {fx.from_currency} → {fx.to_currency}
                  </span>
                  <span className="ml-3 font-mono font-bold text-indigo-600 text-sm">
                    {Number(fx.rate).toFixed(6)}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Effective: {fx.effective_date} | Source: {fx.source}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Retro Adjustments */}
      {activeTab === "adjustments" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Non-Destructive Retroactive Adjustments
          </h3>
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100 text-xs">
            {adjustments && adjustments.length === 0 ? (
              <p className="p-4 text-slate-400 text-center">No pending adjustments recorded.</p>
            ) : (
              adjustments?.map((adj: any) => (
                <div key={adj.id} className="p-3 flex justify-between items-center">
                  <div>
                    <span className="font-semibold text-slate-900">{adj.reason}</span>
                    <span className="ml-2 font-mono font-bold text-emerald-600">
                      +{adj.currency} {Number(adj.amount).toFixed(2)}
                    </span>
                    <span className="ml-2 text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded">
                      {adj.status}
                    </span>
                  </div>
                  <div>
                    {adj.status === "PENDING" && (
                      <button
                        onClick={() => handleProcessAdjustment(adj.id)}
                        className="px-2.5 py-1 bg-indigo-600 text-white rounded text-[11px] font-medium"
                      >
                        Process Adjustment
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab: Reconciliations */}
      {activeTab === "reconciliations" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Multi-Cycle Payroll Reconciliations & Variance
          </h3>
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100 text-xs">
            {reconciliations && reconciliations.length === 0 ? (
              <p className="p-4 text-slate-400 text-center">No reconciliation records generated yet.</p>
            ) : (
              reconciliations?.map((rec: any) => (
                <div key={rec.id} className="p-3 flex justify-between items-center">
                  <div>
                    <span className="font-bold text-slate-900">
                      Run Total: {rec.currency} {Number(rec.calculated_total).toFixed(2)}
                    </span>
                    <span
                      className={`ml-2 text-[10px] font-bold px-2 py-0.5 rounded ${
                        rec.status === "MATCHED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {rec.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Variance: {Number(rec.variance).toFixed(2)} | Baseline: {Number(rec.baseline_total).toFixed(2)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
