"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function StatutoryPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "rules" | "registrations" | "filings" | "calculator">("overview");

  // Data queries
  const { data: schemes } = useSWR("/api/v3/statutory/schemes", fetcher);
  const { data: rules, mutate: mutateRules } = useSWR("/api/v3/statutory/rules", fetcher);
  const { data: registrations, mutate: mutateRegistrations } = useSWR("/api/v3/statutory/registrations", fetcher);
  const { data: filings, mutate: mutateFilings } = useSWR("/api/v3/statutory/filings", fetcher);
  const { data: payments, mutate: mutatePayments } = useSWR("/api/v3/statutory/payments", fetcher);

  // Calculator State
  const [calcPersonId, setCalcPersonId] = useState("");
  const [basicWage, setBasicWage] = useState(25000);
  const [grossWage, setGrossWage] = useState(50000);
  const [stateName, setStateName] = useState("Karnataka");
  const [calcResult, setCalcResult] = useState<any>(null);
  const [calcLoading, setCalcLoading] = useState(false);

  // New Rule Form State
  const [newScheme, setNewScheme] = useState("epf");
  const [newAuthority, setNewAuthority] = useState("epfo");
  const [newEffectiveFrom, setNewEffectiveFrom] = useState("2026-04-01");
  const [newDesc, setNewDesc] = useState("");

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCalcLoading(true);
    try {
      const res = await api.post("/api/v3/statutory/calculate", {
        person_id: calcPersonId || "demo-person",
        basic_wage: Number(basicWage),
        gross_wage: Number(grossWage),
        state: stateName,
      });
      setCalcResult(res.data);
    } catch (err: any) {
      alert("Error executing statutory calculation: " + (err?.response?.data?.detail || err.message));
    } finally {
      setCalcLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">India Statutory Compliance Engine</h1>
        <p className="text-gray-500 text-sm mt-1">
          Module 12: Enterprise EPF, ESI, Professional Tax, TDS with effective-dating, filings, and audit tracking.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 space-x-4">
        {[
          { key: "overview", label: "📊 Compliance Overview" },
          { key: "rules", label: "⚙️ Statutory Rules" },
          { key: "registrations", label: "🏢 Registrations" },
          { key: "filings", label: "📑 Filings & Challans" },
          { key: "calculator", label: "🧮 Wage & Tax Simulator" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`pb-3 px-2 text-sm font-medium border-b-2 transition ${
              activeTab === tab.key
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-gray-500 text-xs font-semibold uppercase">Active Registrations</span>
              <p className="text-2xl font-bold text-gray-900 mt-2">{registrations?.length || 0}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-gray-500 text-xs font-semibold uppercase">Statutory Rules Configured</span>
              <p className="text-2xl font-bold text-gray-900 mt-2">{rules?.length || 0}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-gray-500 text-xs font-semibold uppercase">Upcoming Filings</span>
              <p className="text-2xl font-bold text-gray-900 mt-2">{filings?.length || 0}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-gray-500 text-xs font-semibold uppercase">Payments Recorded</span>
              <p className="text-2xl font-bold text-gray-900 mt-2">{payments?.length || 0}</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Supported Statutory Frameworks</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg border border-gray-100 bg-gray-50">
                <span className="text-sm font-semibold text-blue-700">EPFO (Provident Fund)</span>
                <p className="text-xs text-gray-600 mt-1">12% EE / 12% ER (EPS 8.33% + EPF 3.67%). Statutory cap ₹15,000/mo.</p>
              </div>
              <div className="p-4 rounded-lg border border-gray-100 bg-gray-50">
                <span className="text-sm font-semibold text-emerald-700">ESIC (Medical Insurance)</span>
                <p className="text-xs text-gray-600 mt-1">0.75% EE / 3.25% ER. Wage ceiling ₹21,000/mo gross earnings.</p>
              </div>
              <div className="p-4 rounded-lg border border-gray-100 bg-gray-50">
                <span className="text-sm font-semibold text-purple-700">Professional Tax (PT)</span>
                <p className="text-xs text-gray-600 mt-1">State-specific slabs (Karnataka ₹200, Maharashtra, Tamil Nadu).</p>
              </div>
              <div className="p-4 rounded-lg border border-gray-100 bg-gray-50">
                <span className="text-sm font-semibold text-amber-700">TDS / Income Tax</span>
                <p className="text-xs text-gray-600 mt-1">Section 115BAC New Regime vs Old Regime with 87A rebate.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Rules */}
      {activeTab === "rules" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900">Effective-Dated Statutory Rules</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Scheme</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Authority</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">State</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Effective From</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Effective To</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {rules && rules.length > 0 ? (
                  rules.map((r: any) => (
                    <tr key={r.id}>
                      <td className="px-4 py-3 font-semibold text-gray-900 uppercase">{r.scheme}</td>
                      <td className="px-4 py-3 text-gray-600 uppercase">{r.authority}</td>
                      <td className="px-4 py-3 text-gray-600">{r.state || "All India"}</td>
                      <td className="px-4 py-3 text-gray-600">{r.effective_from}</td>
                      <td className="px-4 py-3 text-gray-600">{r.effective_to || "Indefinite"}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-0.5 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                          Active
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                      No custom rules configured yet. The engine runs on standard India statutory statutory defaults.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Registrations */}
      {activeTab === "registrations" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Legal Entity Statutory Registrations</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Authority</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Registration Number</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">State</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Effective Date</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {registrations && registrations.length > 0 ? (
                  registrations.map((reg: any) => (
                    <tr key={reg.id}>
                      <td className="px-4 py-3 font-semibold uppercase text-gray-900">{reg.authority}</td>
                      <td className="px-4 py-3 font-mono text-gray-800">{reg.registration_number}</td>
                      <td className="px-4 py-3 text-gray-600">{reg.state || "National"}</td>
                      <td className="px-4 py-3 text-gray-600">{reg.effective_date}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                          {reg.status}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                      No statutory registrations recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Filings */}
      {activeTab === "filings" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Statutory Filings, ECR & Returns</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Scheme</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Authority</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Period</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Due Date</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filings && filings.length > 0 ? (
                  filings.map((f: any) => (
                    <tr key={f.id}>
                      <td className="px-4 py-3 font-semibold uppercase">{f.scheme}</td>
                      <td className="px-4 py-3 uppercase text-gray-600">{f.authority}</td>
                      <td className="px-4 py-3 text-gray-600">{f.period_start} to {f.period_end}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{f.due_date}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800 uppercase">
                          {f.status}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                      No filings scheduled or pending.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Wage & Tax Simulator */}
      {activeTab === "calculator" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Run Statutory Deduction Simulator</h3>
            <form onSubmit={handleCalculate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Basic Wage (₹/month)</label>
                <input
                  type="number"
                  value={basicWage}
                  onChange={(e) => setBasicWage(Number(e.target.value))}
                  className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm shadow-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Monthly Gross Salary (₹/month)</label>
                <input
                  type="number"
                  value={grossWage}
                  onChange={(e) => setGrossWage(Number(e.target.value))}
                  className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm shadow-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">State (for Professional Tax)</label>
                <select
                  value={stateName}
                  onChange={(e) => setStateName(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm shadow-sm"
                >
                  <option value="Karnataka">Karnataka</option>
                  <option value="Maharashtra">Maharashtra</option>
                  <option value="Tamil Nadu">Tamil Nadu</option>
                  <option value="Telangana">Telangana</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={calcLoading}
                className="w-full py-2 px-4 rounded-md text-white bg-blue-600 hover:bg-blue-700 font-medium text-sm transition"
              >
                {calcLoading ? "Computing..." : "Calculate Deductions & Contributions"}
              </button>
            </form>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Calculation Results</h3>
            {calcResult ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
                  <div>
                    <span className="text-xs text-gray-500 uppercase">Total Employee Deductions</span>
                    <p className="text-xl font-bold text-red-600">₹{calcResult.total_statutory_deductions}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 uppercase">Total Employer Contributions</span>
                    <p className="text-xl font-bold text-emerald-600">₹{calcResult.total_employer_contributions}</p>
                  </div>
                </div>

                <div className="divide-y divide-gray-100 text-sm">
                  {Object.entries(calcResult.schemes).map(([schemeName, data]: [string, any]) => (
                    <div key={schemeName} className="py-2.5 flex justify-between items-center">
                      <div>
                        <span className="font-semibold text-gray-800 uppercase">{schemeName}</span>
                        {data.note && <p className="text-xs text-gray-400">{data.note}</p>}
                      </div>
                      <div className="text-right">
                        <span className="font-mono text-gray-900 font-medium">₹{data.employee_deduction || 0}</span>
                        {data.employer_contribution > 0 && (
                          <span className="text-xs text-gray-500 block">ER: ₹{data.employer_contribution}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500 py-10 text-center">
                Enter wage parameters and click calculate to simulate live statutory deductions.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
