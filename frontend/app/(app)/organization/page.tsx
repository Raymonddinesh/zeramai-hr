"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function OrganizationPage() {
  const { data: orgData, mutate } = useSWR("/organizations/org-chart", fetcher);
  const [activeTab, setActiveTab] = useState<"chart" | "entities" | "departments">("chart");
  const [showAddDept, setShowAddDept] = useState(false);
  const [deptName, setDeptName] = useState("");
  const [deptCode, setDeptCode] = useState("");

  const handleCreateDept = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deptName || !deptCode) return;
    try {
      await api.post("/organizations/departments", {
        legal_entity_id: orgData?.legal_entities?.[0]?.id || "default",
        name: deptName,
        code: deptCode,
      });
      setDeptName("");
      setDeptCode("");
      setShowAddDept(false);
      mutate();
    } catch {
      alert("Error creating department");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Organization & Multi-Entity Management</h2>
          <p className="text-gray-500 text-sm">
            Phase 0 & 1: Master PRD Multi-Tenant SaaS, Legal Entities, Departments, and Org-Chart hierarchy
          </p>
        </div>
        <button
          onClick={() => setShowAddDept(!showAddDept)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm"
        >
          {showAddDept ? "Cancel" : "+ New Department"}
        </button>
      </div>

      {showAddDept && (
        <div className="bg-white p-6 rounded-xl border border-indigo-100 shadow-sm">
          <h3 className="font-semibold text-gray-800 mb-4">Add New Department</h3>
          <form onSubmit={handleCreateDept} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Department Name</label>
              <input
                type="text"
                required
                value={deptName}
                onChange={(e) => setDeptName(e.target.value)}
                placeholder="e.g. Artificial Intelligence"
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-800"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Department Code</label>
              <input
                type="text"
                required
                value={deptCode}
                onChange={(e) => setDeptCode(e.target.value)}
                placeholder="e.g. AI-LABS"
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-800"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
              >
                Save Department
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("chart")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "chart" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          🌐 Interactive Org Tree
        </button>
        <button
          onClick={() => setActiveTab("entities")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "entities" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          🏢 Legal Entities & Locations
        </button>
        <button
          onClick={() => setActiveTab("departments")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "departments" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          📂 Departments
        </button>
      </div>

      {activeTab === "chart" && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-semibold text-gray-700 mb-4">Enterprise Organization Chart</h3>
          <div className="p-6 bg-gray-50 rounded-xl border border-gray-200 font-mono text-sm space-y-4">
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 bg-indigo-600 text-white rounded-md font-bold text-xs">TENANT</span>
              <span className="font-bold text-gray-900">{orgData?.tenant?.name || "Zeramai Technologies Pvt Ltd"}</span>
              <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded font-sans">Multi-Tenant SaaS</span>
            </div>

            <div className="pl-6 border-l-2 border-indigo-300 space-y-3">
              {(orgData?.legal_entities || []).map((le: any) => (
                <div key={le.id} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-emerald-600 text-white rounded text-xs">LEGAL ENTITY</span>
                    <span className="font-semibold text-gray-800">{le.name}</span>
                    <span className="text-xs text-gray-500">({le.country_code} • {le.currency})</span>
                  </div>

                  <div className="pl-6 border-l-2 border-emerald-300 space-y-1 text-xs font-sans">
                    <p className="font-medium text-gray-500 uppercase tracking-wider text-[10px]">Departments:</p>
                    <div className="flex flex-wrap gap-2">
                      {(le.departments || []).map((d: any) => (
                        <span key={d.id} className="px-2.5 py-1 bg-white border border-gray-300 rounded shadow-sm text-gray-700">
                          📁 {d.name} <span className="text-gray-400 font-mono">({d.code})</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "entities" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(orgData?.legal_entities || []).map((le: any) => (
            <div key={le.id} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-bold text-gray-900">{le.name}</h4>
                  <p className="text-xs text-gray-500">{le.legal_name || le.name}</p>
                </div>
                <span className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs font-semibold">
                  {le.country_code}
                </span>
              </div>
              <div className="text-xs text-gray-600 space-y-1 pt-2 border-t border-gray-100">
                <p><span className="font-medium text-gray-500">Tax Identifier:</span> {le.tax_identifier || "GST-29AABCP1234F1Z5"}</p>
                <p><span className="font-medium text-gray-500">Base Currency:</span> {le.currency || "INR"}</p>
                <p><span className="font-medium text-gray-500">Timezone:</span> {le.timezone || "Asia/Kolkata"}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === "departments" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b">
              <tr>
                <th className="px-6 py-3">Code</th>
                <th className="px-6 py-3">Department Name</th>
                <th className="px-6 py-3">Legal Entity</th>
              </tr>
            </thead>
            <tbody className="divide-y text-gray-700">
              {(orgData?.legal_entities || []).flatMap((le: any) =>
                (le.departments || []).map((d: any) => (
                  <tr key={d.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-mono font-medium text-indigo-600">{d.code}</td>
                    <td className="px-6 py-3 font-semibold text-gray-900">{d.name}</td>
                    <td className="px-6 py-3 text-gray-500">{le.name} ({le.country_code})</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
