"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";


const fetcher = (url: string) => api.get(url).then((r) => r.data);

interface HRPolicy {
  id: string;
  title: string;
  policy_code: string;
  category: string;
  description?: string;
  content: string;
  version: string;
  status: "draft" | "review" | "approved" | "published" | "archived";
  effective_date: string;
  review_date?: string;
  department_id?: string;
  employment_type?: string;
  is_mandatory: boolean;
  previous_version_id?: string;
  created_at: string;
  published_at?: string;
}

interface ComplianceStatus {
  policy_id: string;
  policy_title: string;
  policy_code: string;
  version: string;
  total_eligible_employees: number;
  acknowledged_count: number;
  compliance_rate_pct: number;
}

export default function HRPoliciesPage() {
  const { data: policies, error, isLoading, mutate } = useSWR<HRPolicy[]>("/v3/hr-policies", fetcher);

  const [activeTab, setActiveTab] = useState<"library" | "compliance">("library");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Modals state
  const [isCreatingPolicy, setIsCreatingPolicy] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState<HRPolicy | null>(null);
  const [versioningPolicy, setVersioningPolicy] = useState<HRPolicy | null>(null);
  const [compliancePolicyId, setCompliancePolicyId] = useState<string | null>(null);
  const [complianceData, setComplianceData] = useState<ComplianceStatus | null>(null);
  const [loadingAction, setLoadingAction] = useState(false);

  // New Policy Form State
  const [policyCode, setPolicyCode] = useState("");
  const [policyTitle, setPolicyTitle] = useState("");
  const [policyCategory, setPolicyCategory] = useState("code_of_conduct");
  const [policyDesc, setPolicyDesc] = useState("");
  const [policyContent, setPolicyContent] = useState("");
  const [policyEffectiveDate, setPolicyEffectiveDate] = useState(new Date().toISOString().split("T")[0]);
  const [policyDepartment, setPolicyDepartment] = useState("");
  const [policyEmploymentType, setPolicyEmploymentType] = useState("");
  const [isMandatory, setIsMandatory] = useState(true);

  // New Version Form State
  const [newVersionNum, setNewVersionNum] = useState("");
  const [versionDesc, setVersionDesc] = useState("");
  const [versionContent, setVersionContent] = useState("");
  const [versionEffectiveDate, setVersionEffectiveDate] = useState(new Date().toISOString().split("T")[0]);

  const handleCreatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingAction(true);
    try {
      await api.post("/v3/hr-policies", {
        policy_code: policyCode,
        title: policyTitle,
        category: policyCategory,
        description: policyDesc || undefined,
        content: policyContent,
        effective_date: policyEffectiveDate,
        department_id: policyDepartment || undefined,
        employment_type: policyEmploymentType || undefined,
        is_mandatory: isMandatory,
      });
      setIsCreatingPolicy(false);
      resetCreateForm();
      mutate();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to create policy");
    } finally {
      setLoadingAction(false);
    }
  };

  const handleCreateVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!versioningPolicy) return;
    setLoadingAction(true);
    try {
      await api.post(`/v3/hr-policies/${versioningPolicy.id}/versions`, {
        version: newVersionNum,
        description: versionDesc,
        content: versionContent,
        effective_date: versionEffectiveDate,
      });
      setVersioningPolicy(null);
      mutate();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to create new policy version");
    } finally {
      setLoadingAction(false);
    }
  };

  const handleStatusTransition = async (policyId: string, action: "submit" | "approve" | "publish" | "archive") => {
    setLoadingAction(true);
    try {
      await api.post(`/v3/hr-policies/${policyId}/${action}`);
      mutate();
      if (selectedPolicy && selectedPolicy.id === policyId) {
        const updated = await api.get(`/v3/hr-policies/${policyId}`);
        setSelectedPolicy(updated.data);
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Failed to ${action} policy`);
    } finally {
      setLoadingAction(false);
    }
  };

  const openComplianceModal = async (policy: HRPolicy) => {
    setCompliancePolicyId(policy.id);
    try {
      const res = await api.get(`/v3/hr-policies/${policy.id}/compliance-status`);
      setComplianceData(res.data);
    } catch {
      setComplianceData(null);
    }
  };

  const resetCreateForm = () => {
    setPolicyCode("");
    setPolicyTitle("");
    setPolicyCategory("code_of_conduct");
    setPolicyDesc("");
    setPolicyContent("");
    setPolicyDepartment("");
    setPolicyEmploymentType("");
    setIsMandatory(true);
  };

  const filteredPolicies = (policies || []).filter((p) => {
    if (categoryFilter !== "all" && p.category !== categoryFilter) return false;
    if (statusFilter !== "all" && p.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return p.title.toLowerCase().includes(q) || p.policy_code.toLowerCase().includes(q);
    }
    return true;
  });

  const publishedCount = (policies || []).filter((p) => p.status === "published").length;
  const draftReviewCount = (policies || []).filter((p) => p.status === "draft" || p.status === "review").length;
  const mandatoryCount = (policies || []).filter((p) => p.is_mandatory && p.status === "published").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">HR Policies & Governance</h1>
          <p className="text-sm text-gray-500 mt-1">
            Author, version, publish, and track enterprise policy acknowledgements and regulatory handbooks.
          </p>
        </div>
        <button
          onClick={() => setIsCreatingPolicy(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition shadow-sm"
        >
          <span className="text-base leading-none font-bold">+</span>
          Create Policy
        </button>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Policies</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{policies?.length || 0}</p>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg text-lg">
            📜
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Published & Active</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{publishedCount}</p>
          </div>
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg text-lg">
            ✅
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Draft / In Review</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{draftReviewCount}</p>
          </div>
          <div className="p-3 bg-amber-50 text-amber-600 rounded-lg text-lg">
            ⏳
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Mandatory Handbooks</p>
            <p className="text-2xl font-bold text-indigo-600 mt-1">{mandatoryCount}</p>
          </div>
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg text-lg">
            🛡️
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab("library")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "library"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Policy Library ({policies?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("compliance")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "compliance"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Compliance & Electronic Signatures
          </button>
        </nav>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
        <div className="flex-1 w-full">
          <input
            type="text"
            placeholder="Search by policy title or code..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Categories</option>
            <option value="code_of_conduct">Code of Conduct</option>
            <option value="leave_attendance">Leave & Attendance</option>
            <option value="it_security">IT & Security</option>
            <option value="remote_work">Remote Work</option>
            <option value="compensation_benefits">Compensation & Benefits</option>
            <option value="workplace_safety">Workplace Safety</option>
            <option value="disciplinary">Disciplinary</option>
            <option value="general">General</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="published">Published</option>
            <option value="review">Under Review</option>
            <option value="approved">Approved</option>
            <option value="draft">Draft</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      {/* Table view */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 font-medium">
              <tr>
                <th className="px-6 py-3">Code & Title</th>
                <th className="px-6 py-3">Category</th>
                <th className="px-6 py-3">Version</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Effective Date</th>
                <th className="px-6 py-3">Scope</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                    Loading policies...
                  </td>
                </tr>
              ) : filteredPolicies.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                    No policies found matching the criteria.
                  </td>
                </tr>
              ) : (
                filteredPolicies.map((policy) => (
                  <tr key={policy.id} className="hover:bg-gray-50 transition">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-semibold text-gray-900 flex items-center gap-2">
                          {policy.title}
                          {policy.is_mandatory && (
                            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">
                              Mandatory
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 font-mono mt-0.5">{policy.policy_code}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 capitalize text-gray-600">
                      {policy.category.replace(/_/g, " ")}
                    </td>
                    <td className="px-6 py-4 font-mono font-medium text-gray-800">
                      v{policy.version}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${
                          policy.status === "published"
                            ? "bg-emerald-100 text-emerald-800"
                            : policy.status === "approved"
                            ? "bg-blue-100 text-blue-800"
                            : policy.status === "review"
                            ? "bg-amber-100 text-amber-800"
                            : policy.status === "draft"
                            ? "bg-gray-100 text-gray-800"
                            : "bg-rose-100 text-rose-800"
                        }`}
                      >
                        {policy.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {policy.effective_date}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-500">
                      {policy.department_id ? `Dept: ${policy.department_id}` : "All Departments"}
                      {policy.employment_type && ` • ${policy.employment_type.replace(/_/g, " ")}`}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        onClick={() => setSelectedPolicy(policy)}
                        className="px-2.5 py-1 text-xs font-medium text-indigo-600 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 rounded transition"
                      >
                        Inspect
                      </button>
                      {policy.status === "published" && (
                        <>
                          <button
                            onClick={() => {
                              setVersioningPolicy(policy);
                              setNewVersionNum(`${(parseFloat(policy.version) + 0.1).toFixed(1)}`);
                              setVersionContent(policy.content);
                            }}
                            className="px-2.5 py-1 text-xs font-medium text-purple-600 hover:text-purple-900 bg-purple-50 hover:bg-purple-100 rounded transition"
                          >
                            New Version
                          </button>
                          <button
                            onClick={() => openComplianceModal(policy)}
                            className="px-2.5 py-1 text-xs font-medium text-emerald-600 hover:text-emerald-900 bg-emerald-50 hover:bg-emerald-100 rounded transition"
                          >
                            Compliance
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inspect Policy Modal */}
      {selectedPolicy && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 space-y-6 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-start justify-between border-b pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-gray-900">{selectedPolicy.title}</h2>
                  <span className="font-mono text-sm px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                    v{selectedPolicy.version}
                  </span>
                </div>
                <p className="text-xs text-gray-500 font-mono mt-1">{selectedPolicy.policy_code}</p>
              </div>
              <button
                onClick={() => setSelectedPolicy(null)}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs bg-gray-50 p-4 rounded-xl">
              <div>
                <span className="text-gray-500 block">Category</span>
                <span className="font-semibold text-gray-900 capitalize">{selectedPolicy.category.replace(/_/g, " ")}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Status</span>
                <span className="font-semibold capitalize text-indigo-600">{selectedPolicy.status}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Effective Date</span>
                <span className="font-semibold text-gray-900">{selectedPolicy.effective_date}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Mandatory Ack</span>
                <span className="font-semibold text-gray-900">{selectedPolicy.is_mandatory ? "Yes" : "Optional"}</span>
              </div>
            </div>

            {selectedPolicy.description && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Summary</h4>
                <p className="text-sm text-gray-700 mt-1">{selectedPolicy.description}</p>
              </div>
            )}

            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Policy Document Content</h4>
              <div className="mt-2 p-4 bg-gray-50 rounded-xl border border-gray-200 text-sm text-gray-800 whitespace-pre-wrap font-sans max-h-64 overflow-y-auto leading-relaxed">
                {selectedPolicy.content}
              </div>
            </div>

            {/* Stepper / Action Controls for HR Admin */}
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-xs text-gray-500">
                Created: {new Date(selectedPolicy.created_at).toLocaleDateString()}
              </div>
              <div className="flex items-center gap-2">
                {selectedPolicy.status === "draft" && (
                  <button
                    disabled={loadingAction}
                    onClick={() => handleStatusTransition(selectedPolicy.id, "submit")}
                    className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium"
                  >
                    Submit for Review
                  </button>
                )}
                {selectedPolicy.status === "review" && (
                  <button
                    disabled={loadingAction}
                    onClick={() => handleStatusTransition(selectedPolicy.id, "approve")}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium"
                  >
                    Approve Policy
                  </button>
                )}
                {selectedPolicy.status === "approved" && (
                  <button
                    disabled={loadingAction}
                    onClick={() => handleStatusTransition(selectedPolicy.id, "publish")}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium"
                  >
                    Publish Policy
                  </button>
                )}
                {selectedPolicy.status === "published" && (
                  <button
                    disabled={loadingAction}
                    onClick={() => handleStatusTransition(selectedPolicy.id, "archive")}
                    className="px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-xs font-medium"
                  >
                    Archive
                  </button>
                )}
                <button
                  onClick={() => setSelectedPolicy(null)}
                  className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* New Policy Modal */}
      {isCreatingPolicy && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-lg font-bold text-gray-900">Create New HR Policy</h3>
              <button onClick={() => setIsCreatingPolicy(false)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
                &times;
              </button>
            </div>
            <form onSubmit={handleCreatePolicy} className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Policy Code *</label>
                  <input
                    required
                    type="text"
                    placeholder="e.g. POL-SEC-01"
                    value={policyCode}
                    onChange={(e) => setPolicyCode(e.target.value.toUpperCase())}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 font-mono text-xs uppercase"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Category *</label>
                  <select
                    value={policyCategory}
                    onChange={(e) => setPolicyCategory(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
                  >
                    <option value="code_of_conduct">Code of Conduct</option>
                    <option value="leave_attendance">Leave & Attendance</option>
                    <option value="it_security">IT & Security</option>
                    <option value="remote_work">Remote Work</option>
                    <option value="compensation_benefits">Compensation & Benefits</option>
                    <option value="workplace_safety">Workplace Safety</option>
                    <option value="disciplinary">Disciplinary</option>
                    <option value="general">General</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Policy Title *</label>
                <input
                  required
                  type="text"
                  placeholder="e.g. Enterprise Information Security Policy"
                  value={policyTitle}
                  onChange={(e) => setPolicyTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Executive Summary</label>
                <input
                  type="text"
                  placeholder="Brief synopsis for dashboard preview"
                  value={policyDesc}
                  onChange={(e) => setPolicyDesc(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Policy Content / Articles *</label>
                <textarea
                  required
                  rows={6}
                  placeholder="Full text of policy rules, clauses, and employee responsibilities..."
                  value={policyContent}
                  onChange={(e) => setPolicyContent(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 text-xs font-mono"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Effective Date *</label>
                  <input
                    required
                    type="date"
                    value={policyEffectiveDate}
                    onChange={(e) => setPolicyEffectiveDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Department Scope</label>
                  <input
                    type="text"
                    placeholder="All (or e.g. Engineering)"
                    value={policyDepartment}
                    onChange={(e) => setPolicyDepartment(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Employment Type</label>
                  <select
                    value={policyEmploymentType}
                    onChange={(e) => setPolicyEmploymentType(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white text-xs"
                  >
                    <option value="">All Employment Types</option>
                    <option value="full_time_employee">Full Time Employee</option>
                    <option value="intern">Intern</option>
                    <option value="contractor">Contractor</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="is_mandatory_check"
                  checked={isMandatory}
                  onChange={(e) => setIsMandatory(e.target.checked)}
                  className="w-4 h-4 text-indigo-600 rounded"
                />
                <label htmlFor="is_mandatory_check" className="text-xs text-gray-700">
                  Mandatory Policy — Requires formal employee electronic signature
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setIsCreatingPolicy(false)}
                  className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  disabled={loadingAction}
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium shadow-sm"
                >
                  {loadingAction ? "Creating..." : "Save Draft Policy"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Version Modal */}
      {versioningPolicy && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Create New Policy Version</h3>
                <p className="text-xs text-gray-500">Creating next lineage for {versioningPolicy.title} (current v{versioningPolicy.version})</p>
              </div>
              <button onClick={() => setVersioningPolicy(null)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateVersion} className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">New Version Number *</label>
                  <input
                    required
                    type="text"
                    value={newVersionNum}
                    onChange={(e) => setNewVersionNum(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Effective Date *</label>
                  <input
                    required
                    type="date"
                    value={versionEffectiveDate}
                    onChange={(e) => setVersionEffectiveDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Summary of Version Changes</label>
                <input
                  type="text"
                  placeholder="e.g. Updated guidelines to comply with new 2026 data privacy regulations"
                  value={versionDesc}
                  onChange={(e) => setVersionDesc(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Updated Policy Content *</label>
                <textarea
                  required
                  rows={8}
                  value={versionContent}
                  onChange={(e) => setVersionContent(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 text-xs font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setVersioningPolicy(null)}
                  className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  disabled={loadingAction}
                  type="submit"
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-medium shadow-sm"
                >
                  {loadingAction ? "Saving..." : "Create Version Draft"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Compliance Status Modal */}
      {compliancePolicyId && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Policy Compliance Tracker</h3>
                <p className="text-xs text-gray-500">Live electronic signature analytics</p>
              </div>
              <button onClick={() => setCompliancePolicyId(null)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
                &times;
              </button>
            </div>

            {complianceData ? (
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold text-gray-900">{complianceData.policy_title}</h4>
                  <div className="text-xs font-mono text-gray-500">{complianceData.policy_code} • v{complianceData.version}</div>
                </div>

                <div className="bg-gray-50 p-4 rounded-xl space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Compliance Rate:</span>
                    <span className="font-bold text-emerald-600">{complianceData.compliance_rate_pct}%</span>
                  </div>
                  {/* Progress Bar */}
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, complianceData.compliance_rate_pct)}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-xs pt-2 border-t text-gray-600">
                    <div>
                      <span className="block text-gray-400">Acknowledged:</span>
                      <span className="font-semibold text-gray-900 text-base">{complianceData.acknowledged_count}</span>
                    </div>
                    <div>
                      <span className="block text-gray-400">Total Eligible:</span>
                      <span className="font-semibold text-gray-900 text-base">{complianceData.total_eligible_employees}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-gray-500">Loading compliance data...</div>
            )}

            <div className="flex justify-end pt-4 border-t">
              <button
                onClick={() => setCompliancePolicyId(null)}
                className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
