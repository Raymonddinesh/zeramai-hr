"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function TaxPage() {
  const { data: declarations, mutate } = useSWR("/api/v3/tax/declarations", fetcher);

  const [financialYear, setFinancialYear] = useState("2026-2027");
  const [regime, setRegime] = useState<"new" | "old">("new");
  const [projectedIncome, setProjectedIncome] = useState(1200000);
  const [section80C, setSection80C] = useState(150000);
  const [section80D, setSection80D] = useState(25000);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const deductions = [];
      if (regime === "old") {
        if (section80C > 0) deductions.push({ section: "80C", amount: Number(section80C), name: "Life Insurance, PPF, ELSS" });
        if (section80D > 0) deductions.push({ section: "80D", amount: Number(section80D), name: "Health Insurance" });
      }

      await api.post("/api/v3/tax/declarations", {
        financial_year: financialYear,
        regime,
        projected_income: Number(projectedIncome),
        deductions_json: deductions,
      });

      alert("Tax declaration submitted successfully!");
      mutate();
    } catch (err: any) {
      alert("Error submitting tax declaration: " + (err?.response?.data?.detail || err.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Income Tax & TDS Declarations</h1>
        <p className="text-gray-500 text-sm mt-1">
          Module 12: Section 115BAC tax regime selection, declaration proof management & verification.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Declaration Form */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Annual Tax Declaration</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Financial Year</label>
              <select
                value={financialYear}
                onChange={(e) => setFinancialYear(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm shadow-sm"
              >
                <option value="2026-2027">FY 2026-2027 (AY 2027-2028)</option>
                <option value="2025-2026">FY 2025-2026 (AY 2026-2027)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Tax Regime</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRegime("new")}
                  className={`p-3 text-left rounded-lg border text-sm font-medium transition ${
                    regime === "new"
                      ? "border-blue-600 bg-blue-50 text-blue-800"
                      : "border-gray-200 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <span className="block font-semibold">New Regime</span>
                  <span className="text-xs text-gray-500">Lower tax slabs, ₹75k std deduction, 87A rebate to ₹7L</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRegime("old")}
                  className={`p-3 text-left rounded-lg border text-sm font-medium transition ${
                    regime === "old"
                      ? "border-blue-600 bg-blue-50 text-blue-800"
                      : "border-gray-200 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <span className="block font-semibold">Old Regime</span>
                  <span className="text-xs text-gray-500">Allows 80C, 80D, HRA & Home Loan exemptions</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Projected Annual Income (₹)</label>
              <input
                type="number"
                value={projectedIncome}
                onChange={(e) => setProjectedIncome(Number(e.target.value))}
                className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm shadow-sm"
                required
              />
            </div>

            {regime === "old" && (
              <div className="space-y-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Itemized Deductions</h4>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Section 80C (Max ₹1,50,000)</label>
                  <input
                    type="number"
                    value={section80C}
                    onChange={(e) => setSection80C(Number(e.target.value))}
                    max={150000}
                    className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-xs shadow-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Section 80D (Health Insurance)</label>
                  <input
                    type="number"
                    value={section80D}
                    onChange={(e) => setSection80D(Number(e.target.value))}
                    className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-xs shadow-sm"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 rounded-md text-white bg-blue-600 hover:bg-blue-700 font-medium text-sm transition"
            >
              {isSubmitting ? "Submitting..." : "Submit Declaration"}
            </button>
          </form>
        </div>

        {/* Declarations History Table */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Submitted Tax Declarations</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Financial Year</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Regime</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Projected CTC</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Deductions</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {declarations && declarations.length > 0 ? (
                  declarations.map((d: any) => (
                    <tr key={d.id}>
                      <td className="px-4 py-3 font-semibold text-gray-900">{d.financial_year}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 uppercase">
                          {d.regime}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-gray-800">₹{Number(d.projected_income).toLocaleString()}</td>
                      <td className="px-4 py-3 text-gray-600">
                        {d.deductions_json?.length || 0} claimed
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                            d.status === "verified"
                              ? "bg-green-100 text-green-800"
                              : d.status === "rejected"
                              ? "bg-red-100 text-red-800"
                              : "bg-amber-100 text-amber-800"
                          } uppercase`}
                        >
                          {d.status}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                      No tax declarations found. Submit your declaration using the form on the left.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
