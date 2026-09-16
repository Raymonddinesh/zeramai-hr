"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function CompliancePage() {
  const { data: policies, mutate: mutatePolicies } = useSWR("/compliance/policies", fetcher);
  const { data: grievances, mutate: mutateGrievances } = useSWR("/compliance/grievances", fetcher);

  const [activeTab, setActiveTab] = useState<"policies" | "grievances">("policies");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("general");
  const [isAnonymous, setIsAnonymous] = useState(false);

  const handleAcknowledge = async (policyId: string) => {
    try {
      const res = await api.post(`/compliance/policies/${policyId}/acknowledge`);
      alert(res.data.message || "Policy acknowledged successfully!");
      mutatePolicies();
    } catch {
      alert("Error acknowledging policy");
    }
  };

  const handleSubmitGrievance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !description) return;
    try {
      const res = await api.post("/compliance/grievances", {
        title,
        description,
        category,
        is_anonymous: isAnonymous,
      });
      alert(`Grievance submitted successfully!\nTicket Number: ${res.data.ticket_number}`);
      setTitle("");
      setDescription("");
      mutateGrievances();
    } catch {
      alert("Error submitting grievance");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Compliance, Policy Center & Grievance</h2>
        <p className="text-gray-500 text-sm">
          Phase 12: Mandatory governance policies with digital e-signatures & confidential whistleblower ticketing
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("policies")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "policies"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          📜 Company Compliance Policies
        </button>
        <button
          onClick={() => setActiveTab("grievances")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "grievances"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          🛡️ Whistleblower & Grievance Desk
        </button>
      </div>

      {activeTab === "policies" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {(policies || []).map((p: any) => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-bold text-gray-900 text-base">{p.title}</h4>
                  <p className="text-xs text-gray-500">Version {p.version} • Effective: {p.effective_date}</p>
                </div>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">
                  {p.category}
                </span>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg text-xs text-gray-700 leading-relaxed font-sans">
                {p.content || "All workforce members must maintain zero tolerance for non-compliance and adhere to confidentiality rules."}
              </div>

              <button
                onClick={() => handleAcknowledge(p.id)}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs py-2 rounded-lg font-medium shadow-sm transition"
              >
                ✍️ Electronically Sign & Acknowledge
              </button>
            </div>
          ))}
          {(!policies || policies.length === 0) && (
            <p className="text-sm text-gray-400 py-8 col-span-2 text-center">No active policies published.</p>
          )}
        </div>
      )}

      {activeTab === "grievances" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Submit form */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <h3 className="font-semibold text-gray-800">Submit Confidential Report</h3>
            <form onSubmit={handleSubmitGrievance} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-gray-700 mb-1">Issue Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Workplace safety or ethics concern"
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                />
              </div>
              <div>
                <label className="block font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                >
                  <option value="general">General</option>
                  <option value="ethics_violation">Ethics Violation</option>
                  <option value="harassment">Harassment</option>
                  <option value="compensation_dispute">Compensation Dispute</option>
                  <option value="safety_health">Safety & Health</option>
                </select>
              </div>
              <div>
                <label className="block font-medium text-gray-700 mb-1">Detailed Description</label>
                <textarea
                  rows={4}
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Provide detailed facts. All reports are encrypted and strictly protected."
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                ></textarea>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="anon"
                  checked={isAnonymous}
                  onChange={(e) => setIsAnonymous(e.target.checked)}
                  className="rounded text-indigo-600"
                />
                <label htmlFor="anon" className="text-gray-700 font-medium">Submit Anonymously (Whistleblower)</label>
              </div>
              <button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition"
              >
                Submit Grievance Ticket
              </button>
            </form>
          </div>

          {/* Grievances listing */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
            <h3 className="font-semibold text-gray-800 text-sm">Grievance Audit Register</h3>
            <div className="space-y-3">
              {(grievances || []).map((g: any) => (
                <div key={g.id} className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-1.5">
                  <div className="flex justify-between items-center">
                    <span className="font-mono font-bold text-xs text-indigo-700">{g.ticket_number}</span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 bg-amber-100 text-amber-800 rounded">
                      {g.status}
                    </span>
                  </div>
                  <h5 className="font-semibold text-sm text-gray-900">{g.title}</h5>
                  <p className="text-xs text-gray-500">
                    Category: <span className="capitalize">{g.category?.replace("_", " ")}</span> • Identity:{" "}
                    {g.is_anonymous ? "🛡️ Anonymous Whistleblower" : "Identified Employee"}
                  </p>
                </div>
              ))}
              {(!grievances || grievances.length === 0) && (
                <p className="text-xs text-gray-400 py-8 text-center">No grievance cases filed.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
