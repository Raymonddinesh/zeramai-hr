"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function GlobalPayrollHubPage() {
  const { user } = useAuth();
  const [selectedPayslip, setSelectedPayslip] = useState<any | null>(null);

  // Queries
  const { data: countries } = useSWR("/api/v3/global-payroll/countries", fetcher);
  const { data: payGroups } = useSWR("/api/v3/global-payroll/pay-groups", fetcher);
  const { data: calendars } = useSWR("/api/v3/global-payroll/calendars", fetcher);
  const { data: fxRates } = useSWR("/api/v3/global-payroll/exchange-rates", fetcher);
  const { data: payslips } = useSWR("/api/v3/global-payroll/payslips", fetcher);

  const isPrivileged = user && ["super_admin", "hr_admin", "finance"].includes(user.role);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🌐</span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Global Payroll & Multi-Country Hub
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Enterprise gross-to-net processing, statutory multi-country engines & FX currency management
          </p>
        </div>
        {isPrivileged && (
          <div className="flex items-center gap-3">
            <Link
              href="/admin/global-payroll"
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
            >
              <span>⚙️</span>
              <span>Global Payroll Admin</span>
            </Link>
          </div>
        )}
      </div>

      {/* KPI Header Cards (Privileged) */}
      {isPrivileged && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Operating Countries
            </p>
            <div className="flex items-baseline justify-between mt-2">
              <span className="text-2xl font-bold text-slate-900">
                {countries ? countries.length : "—"}
              </span>
              <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                7 Standard Tier-1
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">IND, USA, GBR, CAN, AUS, SGP, UAE</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Active Pay Groups
            </p>
            <div className="flex items-baseline justify-between mt-2">
              <span className="text-2xl font-bold text-indigo-600">
                {payGroups ? payGroups.length : "—"}
              </span>
              <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                Multi-Entity
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Isolated Legal Entity calendars</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Active Payroll Calendars
            </p>
            <div className="flex items-baseline justify-between mt-2">
              <span className="text-2xl font-bold text-amber-600">
                {calendars ? calendars.length : "—"}
              </span>
              <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
                Strict Periods
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Overlap prevented & verified</p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Live FX Rates
            </p>
            <div className="flex items-baseline justify-between mt-2">
              <span className="text-2xl font-bold text-teal-600">
                {fxRates ? fxRates.length : "—"}
              </span>
              <span className="text-xs font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                Immutable Snapshots
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Historical audit trail locked</p>
          </div>
        </div>
      )}

      {/* Employee Payslip History Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <span>📄</span> My Official Global Payslips
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Secure employee self-service view with cryptographically verified salary statements
            </p>
          </div>
          <span className="text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 px-2.5 py-1 rounded-full">
            {payslips ? `${payslips.length} Records` : "Loading..."}
          </span>
        </div>

        {payslips && payslips.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-500">No payslips currently released for your profile.</p>
            <p className="text-xs text-slate-400 mt-1">
              Payslips are automatically generated and published once your pay group calendar is finalized.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {payslips?.map((slip: any) => (
              <div
                key={slip.id}
                className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/80 transition"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900 text-sm">
                      {slip.payroll_calendar?.name || "Standard Payroll Run"}
                    </span>
                    <span className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono font-medium">
                      {slip.payslip_number}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Period: {slip.payroll_calendar?.period_start} to {slip.payroll_calendar?.period_end}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Released: {new Date(slip.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-[11px] text-slate-500 font-medium uppercase tracking-wider">
                      Net Take-Home
                    </p>
                    <p className="text-lg font-bold text-emerald-600">
                      {slip.currency} {Number(slip.net_pay).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-[10px] text-slate-400">
                      Gross: {slip.currency} {Number(slip.gross_pay).toLocaleString()}
                    </p>
                  </div>

                  <button
                    onClick={() => setSelectedPayslip(slip)}
                    className="px-3.5 py-1.5 bg-slate-900 hover:bg-black text-white text-xs font-medium rounded-lg shadow-sm transition"
                  >
                    View Breakdown
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Payslip Detail Modal */}
      {selectedPayslip && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start border-b border-slate-200 pb-4">
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-indigo-600">
                  Global Payslip Breakdown
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  {selectedPayslip.payroll_calendar?.name || "Global Payroll Cycle"}
                </h3>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Ref: {selectedPayslip.payslip_number}
                </p>
              </div>
              <button
                onClick={() => setSelectedPayslip(null)}
                className="text-slate-400 hover:text-slate-700 text-lg p-1"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl">
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Gross Earnings</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">
                  {selectedPayslip.currency} {Number(selectedPayslip.gross_pay).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Total Deductions</p>
                <p className="text-sm font-bold text-rose-600 mt-0.5">
                  - {selectedPayslip.currency} {Number(selectedPayslip.total_deductions).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Taxes Withheld</p>
                <p className="text-sm font-bold text-amber-600 mt-0.5">
                  - {selectedPayslip.currency} {Number(selectedPayslip.total_taxes).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Net Pay</p>
                <p className="text-sm font-bold text-emerald-600 mt-0.5">
                  {selectedPayslip.currency} {Number(selectedPayslip.net_pay).toFixed(2)}
                </p>
              </div>
            </div>

            {/* Line Items Breakdown */}
            {selectedPayslip.component_breakdown && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Itemized Component Schedule
                </h4>
                <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100 text-xs">
                  {selectedPayslip.component_breakdown.map((item: any, idx: number) => (
                    <div key={idx} className="p-2.5 flex justify-between items-center">
                      <div>
                        <span className="font-semibold text-slate-800">{item.component_name}</span>
                        <span className="ml-2 text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                          {item.component_type}
                        </span>
                        {item.calculation_reference && (
                          <p className="text-[11px] text-slate-400 mt-0.5">{item.calculation_reference}</p>
                        )}
                      </div>
                      <div className="font-mono font-medium text-slate-900">
                        {item.currency} {Number(item.amount).toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedPayslip(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition"
              >
                Close Statement
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Country Engine Directory (Privileged View) */}
      {isPrivileged && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <span>🌍</span> Multi-Country Compliance & Engine Framework
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Standard Tier-1 country registry with statutory engines & integration adapters
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {countries?.map((c: any) => (
              <div
                key={c.id}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition space-y-2"
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{c.country_name}</span>
                    <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded font-mono font-bold">
                      {c.country_code}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                      c.status === "PRODUCTION_VALIDATED"
                        ? "bg-emerald-100 text-emerald-800"
                        : c.status === "FRAMEWORK_READY"
                        ? "bg-indigo-100 text-indigo-800"
                        : "bg-slate-200 text-slate-700"
                    }`}
                  >
                    {c.status}
                  </span>
                </div>

                <div className="text-xs text-slate-500 space-y-1">
                  <p>Default Currency: <strong className="text-slate-700">{c.default_currency}</strong></p>
                  <p>Tax Year: <strong className="text-slate-700">{c.tax_year_start} to {c.tax_year_end}</strong></p>
                  <p>Statutory Engine: <span className="font-mono text-[11px] text-indigo-600">{c.statutory_engine_type}</span></p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
