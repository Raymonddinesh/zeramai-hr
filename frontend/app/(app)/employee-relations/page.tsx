"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";


const fetcher = (url: string) => api.get(url).then((r) => r.data);

interface ERCaseNote {
  id: string;
  case_id: string;
  author_id: string;
  author_name?: string;
  note_type: string;
  content: string;
  is_confidential: boolean;
  created_at: string;
}

interface ERCase {
  id: string;
  case_number: string;
  title: string;
  category: string;
  severity: "low" | "medium" | "high" | "critical";
  subject_person_id: string;
  subject_person_name?: string;
  reporting_manager_id?: string;
  hr_owner_id: string;
  hr_owner_name?: string;
  created_by_id: string;
  status: "open" | "under_review" | "investigation" | "action_required" | "resolved" | "closed";
  description: string;
  investigation_summary?: string;
  resolution_summary?: string;
  created_at: string;
  updated_at: string;
  closed_at?: string;
  notes: ERCaseNote[];
  disciplinary_actions_count: number;
}

interface DisciplinaryAction {
  id: string;
  case_id?: string;
  person_id: string;
  person_name?: string;
  action_type: string;
  reason: string;
  action_plan?: string;
  issued_by_id: string;
  issued_date: string;
  effective_date: string;
  expiry_date?: string;
  status: string;
  employee_acknowledged: boolean;
  acknowledged_at?: string;
  created_at: string;
}

export default function EmployeeRelationsPage() {
  const { data: cases, error: casesError, isLoading: casesLoading, mutate: mutateCases } =
    useSWR<ERCase[]>("/v3/employee-relations/cases", fetcher);
  const { data: disciplinaryActions, mutate: mutateDisciplinary } =
    useSWR<DisciplinaryAction[]>("/v3/employee-relations/disciplinary", fetcher);
  const { data: employees } = useSWR<any[]>("/employees", fetcher);

  const [activeTab, setActiveTab] = useState<"cases" | "disciplinary">("cases");
  const [statusFilter, setStatusFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");

  // Modals state
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [selectedCase, setSelectedCase] = useState<ERCase | null>(null);
  const [isIssuingDisciplinary, setIsIssuingDisciplinary] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);

  // New Case Form State
  const [caseTitle, setCaseTitle] = useState("");
  const [caseCategory, setCaseCategory] = useState("performance");
  const [caseSeverity, setCaseSeverity] = useState<"low" | "medium" | "high" | "critical">("medium");
  const [caseSubjectId, setCaseSubjectId] = useState("");
  const [caseDescription, setCaseDescription] = useState("");
  const [caseInvestigationSummary, setCaseInvestigationSummary] = useState("");

  // Add Note Form State
  const [noteType, setNoteType] = useState("internal_hr");
  const [noteContent, setNoteContent] = useState("");
  const [noteConfidential, setNoteConfidential] = useState(true);

  // Disciplinary Form State
  const [discType, setDiscType] = useState("written_warning");
  const [discReason, setDiscReason] = useState("");
  const [discActionPlan, setDiscActionPlan] = useState("");
  const [discEffectiveDate, setDiscEffectiveDate] = useState(new Date().toISOString().split("T")[0]);
  const [discExpiryDate, setDiscExpiryDate] = useState("");

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingAction(true);
    try {
      await api.post("/v3/employee-relations/cases", {
        title: caseTitle,
        category: caseCategory,
        severity: caseSeverity,
        subject_person_id: caseSubjectId,
        description: caseDescription,
        investigation_summary: caseInvestigationSummary || undefined,
      });
      setIsCreatingCase(false);
      resetCaseForm();
      mutateCases();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to create ER case");
    } finally {
      setLoadingAction(false);
    }
  };

  const handleUpdateStatus = async (caseId: string, newStatus: string, reasonSummary?: string) => {
    setLoadingAction(true);
    try {
      await api.post(`/v3/employee-relations/cases/${caseId}/status`, {
        status: newStatus,
        resolution_summary: newStatus === "resolved" ? reasonSummary : undefined,
      });
      mutateCases();
      if (selectedCase && selectedCase.id === caseId) {
        const updated = await api.get(`/v3/employee-relations/cases/${caseId}`);
        setSelectedCase(updated.data);
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to update case status");
    } finally {
      setLoadingAction(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase || !noteContent.trim()) return;
    setLoadingAction(true);
    try {
      await api.post(`/v3/employee-relations/cases/${selectedCase.id}/notes`, {
        note_type: noteType,
        content: noteContent,
        is_confidential: noteConfidential,
      });
      setNoteContent("");
      const updated = await api.get(`/v3/employee-relations/cases/${selectedCase.id}`);
      setSelectedCase(updated.data);
      mutateCases();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to add case note");
    } finally {
      setLoadingAction(false);
    }
  };

  const handleIssueDisciplinary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;
    setLoadingAction(true);
    try {
      await api.post(`/v3/employee-relations/cases/${selectedCase.id}/disciplinary`, {
        person_id: selectedCase.subject_person_id,
        action_type: discType,
        reason: discReason,
        action_plan: discActionPlan || undefined,
        effective_date: discEffectiveDate,
        expiry_date: discExpiryDate || undefined,
      });
      setIsIssuingDisciplinary(false);
      resetDiscForm();
      mutateDisciplinary();
      mutateCases();
      const updated = await api.get(`/v3/employee-relations/cases/${selectedCase.id}`);
      setSelectedCase(updated.data);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to issue disciplinary action");
    } finally {
      setLoadingAction(false);
    }
  };

  const resetCaseForm = () => {
    setCaseTitle("");
    setCaseCategory("performance");
    setCaseSeverity("medium");
    setCaseSubjectId("");
    setCaseDescription("");
    setCaseInvestigationSummary("");
  };

  const resetDiscForm = () => {
    setDiscType("written_warning");
    setDiscReason("");
    setDiscActionPlan("");
    setDiscExpiryDate("");
  };

  const filteredCases = (cases || []).filter((c) => {
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    if (severityFilter !== "all" && c.severity !== severityFilter) return false;
    return true;
  });

  const activeCasesCount = (cases || []).filter((c) => c.status !== "closed" && c.status !== "resolved").length;
  const investigationCount = (cases || []).filter((c) => c.status === "investigation").length;
  const actionRequiredCount = (cases || []).filter((c) => c.status === "action_required").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Employee Relations (ER) Hub</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage workplace conduct, investigations, performance interventions, and formal disciplinary proceedings.
          </p>
        </div>
        <button
          onClick={() => setIsCreatingCase(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium transition shadow-sm"
        >
          <span className="font-bold text-base leading-none">+</span>
          Open ER Case
        </button>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Active ER Cases</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{activeCasesCount}</p>
          </div>
          <div className="p-3 bg-rose-50 text-rose-600 rounded-lg text-lg">
            🛡️
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Under Investigation</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{investigationCount}</p>
          </div>
          <div className="p-3 bg-amber-50 text-amber-600 rounded-lg text-lg">
            ⏳
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Action Required</p>
            <p className="text-2xl font-bold text-orange-600 mt-1">{actionRequiredCount}</p>
          </div>
          <div className="p-3 bg-orange-50 text-orange-600 rounded-lg text-lg">
            ⚠️
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Disciplinary Issued</p>
            <p className="text-2xl font-bold text-purple-600 mt-1">{disciplinaryActions?.length || 0}</p>
          </div>
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg text-lg">
            ⚖️
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab("cases")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "cases"
                ? "border-rose-600 text-rose-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Case Management Queue ({cases?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("disciplinary")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === "disciplinary"
                ? "border-rose-600 text-rose-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Disciplinary Actions Log ({disciplinaryActions?.length || 0})
          </button>
        </nav>
      </div>

      {activeTab === "cases" ? (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm bg-white focus:ring-2 focus:ring-rose-500"
            >
              <option value="all">All Case Statuses</option>
              <option value="open">Open</option>
              <option value="under_review">Under Review</option>
              <option value="investigation">Investigation</option>
              <option value="action_required">Action Required</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm bg-white focus:ring-2 focus:ring-rose-500"
            >
              <option value="all">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Cases Table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 border-b text-gray-500 font-medium">
                  <tr>
                    <th className="px-6 py-3">Case ID & Title</th>
                    <th className="px-6 py-3">Subject Employee</th>
                    <th className="px-6 py-3">Category</th>
                    <th className="px-6 py-3">Severity</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">HR Owner</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {casesLoading ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                        Loading employee relations cases...
                      </td>
                    </tr>
                  ) : filteredCases.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                        No cases found matching filters.
                      </td>
                    </tr>
                  ) : (
                    filteredCases.map((c) => (
                      <tr key={c.id} className="hover:bg-gray-50 transition">
                        <td className="px-6 py-4">
                          <div className="font-semibold text-gray-900">{c.title}</div>
                          <div className="text-xs font-mono text-gray-500 mt-0.5">{c.case_number}</div>
                        </td>
                        <td className="px-6 py-4 font-medium text-gray-800">
                          {c.subject_person_name || "Unknown"}
                        </td>
                        <td className="px-6 py-4 capitalize text-gray-600">
                          {c.category.replace(/_/g, " ")}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider ${
                              c.severity === "critical"
                                ? "bg-rose-100 text-rose-800"
                                : c.severity === "high"
                                ? "bg-orange-100 text-orange-800"
                                : c.severity === "medium"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-blue-100 text-blue-800"
                            }`}
                          >
                            {c.severity}
                          </span>
                        </td>
                        <td className="px-6 py-4 capitalize">
                          <span
                            className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              c.status === "closed" || c.status === "resolved"
                                ? "bg-emerald-100 text-emerald-800"
                                : c.status === "action_required"
                                ? "bg-rose-100 text-rose-800"
                                : c.status === "investigation"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {c.status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs text-gray-600">
                          {c.hr_owner_name || "Unassigned"}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={async () => {
                              const res = await api.get(`/v3/employee-relations/cases/${c.id}`);
                              setSelectedCase(res.data);
                            }}
                            className="px-3 py-1 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded text-xs font-medium transition"
                          >
                            View Case
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Disciplinary Actions Table */
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 border-b text-gray-500 font-medium">
                <tr>
                  <th className="px-6 py-3">Employee</th>
                  <th className="px-6 py-3">Action Type</th>
                  <th className="px-6 py-3">Reason / Details</th>
                  <th className="px-6 py-3">Issued Date</th>
                  <th className="px-6 py-3">Effective Range</th>
                  <th className="px-6 py-3">Employee Ack</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {(disciplinaryActions || []).length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                      No formal disciplinary actions on record.
                    </td>
                  </tr>
                ) : (
                  disciplinaryActions?.map((d) => (
                    <tr key={d.id} className="hover:bg-gray-50 transition">
                      <td className="px-6 py-4 font-semibold text-gray-900">
                        {d.person_name || d.person_id}
                      </td>
                      <td className="px-6 py-4">
                        <span className="font-medium text-xs uppercase px-2 py-0.5 rounded bg-purple-100 text-purple-800">
                          {d.action_type.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-700 text-xs max-w-xs truncate">
                        {d.reason}
                      </td>
                      <td className="px-6 py-4 text-gray-600 text-xs">{d.issued_date}</td>
                      <td className="px-6 py-4 text-gray-600 text-xs">
                        {d.effective_date} {d.expiry_date ? `to ${d.expiry_date}` : "(indefinite)"}
                      </td>
                      <td className="px-6 py-4">
                        {d.employee_acknowledged ? (
                          <span className="inline-flex items-center gap-1 text-emerald-700 text-xs font-medium">
                            ✓ Acknowledged
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-700 text-xs font-medium">
                            ⏳ Pending Ack
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Case Details Drawer / Modal */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full p-6 space-y-6 max-h-[90vh] overflow-y-auto shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b pb-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-bold text-gray-900">{selectedCase.title}</h2>
                  <span className="font-mono text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-700">
                    {selectedCase.case_number}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                  <span>Subject: <strong>{selectedCase.subject_person_name}</strong></span>
                  <span>•</span>
                  <span>Category: <strong className="capitalize">{selectedCase.category.replace(/_/g, " ")}</strong></span>
                  <span>•</span>
                  <span>Severity: <strong className="uppercase">{selectedCase.severity}</strong></span>
                </div>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            {/* Stepper / Lifecycle Bar */}
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100 flex items-center justify-between text-xs">
              <span className="font-semibold text-gray-700">
                Status: <span className="uppercase text-rose-600 font-bold">{selectedCase.status.replace(/_/g, " ")}</span>
              </span>
              <div className="flex items-center gap-2">
                {selectedCase.status === "open" && (
                  <button
                    onClick={() => handleUpdateStatus(selectedCase.id, "under_review")}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium"
                  >
                    Start Review
                  </button>
                )}
                {selectedCase.status === "under_review" && (
                  <button
                    onClick={() => handleUpdateStatus(selectedCase.id, "investigation")}
                    className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded font-medium"
                  >
                    Open Investigation
                  </button>
                )}
                {selectedCase.status === "investigation" && (
                  <button
                    onClick={() => handleUpdateStatus(selectedCase.id, "action_required")}
                    className="px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white rounded font-medium"
                  >
                    Require Action
                  </button>
                )}
                {selectedCase.status === "action_required" && (
                  <button
                    onClick={() => handleUpdateStatus(selectedCase.id, "resolved", "Intervention plan agreed and completed.")}
                    className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium"
                  >
                    Mark Resolved
                  </button>
                )}
                {selectedCase.status === "resolved" && (
                  <button
                    onClick={() => handleUpdateStatus(selectedCase.id, "closed")}
                    className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded font-medium"
                  >
                    Close Case
                  </button>
                )}
                <button
                  onClick={() => setIsIssuingDisciplinary(true)}
                  className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium flex items-center gap-1"
                >
                  <span>⚖️</span>
                  Issue Disciplinary
                </button>
              </div>
            </div>

            {/* Case Details */}
            <div className="space-y-3 text-xs">
              <h4 className="font-semibold text-gray-500 uppercase tracking-wider">Initial Allegation / Description</h4>
              <div className="p-3 bg-gray-50 rounded-lg text-gray-800 leading-relaxed">
                {selectedCase.description}
              </div>

              {selectedCase.investigation_summary && (
                <div>
                  <h4 className="font-semibold text-rose-600 uppercase tracking-wider flex items-center gap-1">
                    <span>🔒</span>
                    Investigation Summary (HR Confidential)
                  </h4>
                  <div className="p-3 bg-rose-50/50 border border-rose-100 rounded-lg text-gray-800 mt-1">
                    {selectedCase.investigation_summary}
                  </div>
                </div>
              )}

              {selectedCase.resolution_summary && (
                <div>
                  <h4 className="font-semibold text-emerald-600 uppercase tracking-wider">Resolution Summary</h4>
                  <div className="p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg text-gray-800 mt-1">
                    {selectedCase.resolution_summary}
                  </div>
                </div>
              )}
            </div>

            {/* Notes Timeline */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Case Activity & Confidential Notes ({selectedCase.notes?.length || 0})
              </h4>
              <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                {selectedCase.notes?.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No notes recorded yet.</p>
                ) : (
                  selectedCase.notes?.map((n) => (
                    <div
                      key={n.id}
                      className={`p-3 rounded-lg border text-xs ${
                        n.is_confidential
                          ? "bg-amber-50/60 border-amber-200"
                          : "bg-gray-50 border-gray-200"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] text-gray-500 mb-1">
                        <span className="font-medium text-gray-700 flex items-center gap-1">
                          {n.author_name || "HR Staff"}
                          {n.is_confidential && (
                            <span className="px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 font-bold uppercase text-[9px] flex items-center gap-0.5">
                              🔒 Confidential
                            </span>
                          )}
                        </span>
                        <span>{new Date(n.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-gray-800 whitespace-pre-wrap">{n.content}</p>
                    </div>
                  ))
                )}
              </div>

              {/* Add Note Form */}
              <form onSubmit={handleAddNote} className="space-y-2 pt-2 border-t text-xs">
                <div className="flex items-center gap-3">
                  <select
                    value={noteType}
                    onChange={(e) => setNoteType(e.target.value)}
                    className="px-2.5 py-1.5 border rounded-lg bg-white text-xs"
                  >
                    <option value="internal_hr">Internal HR Remark</option>
                    <option value="investigation">Investigation Evidence</option>
                    <option value="employee_communication">Employee Communication</option>
                  </select>
                  <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={noteConfidential}
                      onChange={(e) => setNoteConfidential(e.target.checked)}
                      className="w-3.5 h-3.5 text-rose-600 rounded"
                    />
                    Mark as Confidential (HR Only)
                  </label>
                </div>
                <div className="flex gap-2">
                  <textarea
                    required
                    rows={2}
                    placeholder="Add documentation, interview summary, or case update..."
                    value={noteContent}
                    onChange={(e) => setNoteContent(e.target.value)}
                    className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-rose-500 text-xs"
                  />
                  <button
                    disabled={loadingAction}
                    type="submit"
                    className="px-4 py-2 bg-gray-900 hover:bg-black text-white rounded-lg text-xs font-medium self-end"
                  >
                    Add Note
                  </button>
                </div>
              </form>
            </div>

            <div className="flex justify-end pt-4 border-t">
              <button
                onClick={() => setSelectedCase(null)}
                className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Case Modal */}
      {isCreatingCase && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-lg font-bold text-gray-900">Open Employee Relations Case</h3>
              <button onClick={() => setIsCreatingCase(false)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateCase} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Subject Employee *</label>
                <select
                  required
                  value={caseSubjectId}
                  onChange={(e) => setCaseSubjectId(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-rose-500 bg-white text-xs"
                >
                  <option value="">Select Employee...</option>
                  {(employees || []).map((emp) => (
                    <option key={emp.person_id || emp.id} value={emp.person_id || emp.id}>
                      {emp.full_name || emp.name} ({emp.department || "No Dept"})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Case Title *</label>
                <input
                  required
                  type="text"
                  placeholder="e.g. Unexcused Repeated Absences"
                  value={caseTitle}
                  onChange={(e) => setCaseTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-rose-500 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Category *</label>
                  <select
                    value={caseCategory}
                    onChange={(e) => setCaseCategory(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-rose-500 bg-white text-xs"
                  >
                    <option value="conduct">Conduct & Ethics</option>
                    <option value="attendance">Attendance & Punctuality</option>
                    <option value="performance">Performance Deficiency</option>
                    <option value="workplace_behavior">Workplace Behavior</option>
                    <option value="policy_violation">Policy Violation</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Severity *</label>
                  <select
                    value={caseSeverity}
                    onChange={(e) => setCaseSeverity(e.target.value as any)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-rose-500 bg-white text-xs"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description / Incident Summary *</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Provide background, dates, and observed behavior..."
                  value={caseDescription}
                  onChange={(e) => setCaseDescription(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-rose-500 text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Initial Investigation Notes (Confidential)</label>
                <textarea
                  rows={2}
                  placeholder="Confidential notes visible only to HR..."
                  value={caseInvestigationSummary}
                  onChange={(e) => setCaseInvestigationSummary(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-rose-500 text-xs bg-amber-50/40"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setIsCreatingCase(false)}
                  className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  disabled={loadingAction}
                  type="submit"
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-medium shadow-sm"
                >
                  {loadingAction ? "Opening..." : "Open Case"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Issue Disciplinary Action Modal */}
      {isIssuingDisciplinary && selectedCase && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Issue Disciplinary Action</h3>
                <p className="text-xs text-gray-500">For {selectedCase.subject_person_name} ({selectedCase.case_number})</p>
              </div>
              <button onClick={() => setIsIssuingDisciplinary(false)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
                &times;
              </button>
            </div>
            <form onSubmit={handleIssueDisciplinary} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Disciplinary Action Type *</label>
                <select
                  value={discType}
                  onChange={(e) => setDiscType(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 bg-white text-xs"
                >
                  <option value="verbal_warning">Verbal Warning</option>
                  <option value="written_warning">Written Warning</option>
                  <option value="final_warning">Final Written Warning</option>
                  <option value="pip">Performance Improvement Plan (PIP)</option>
                  <option value="suspension">Suspension</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Specific Reason & Grounds *</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Detail the infraction, relevant policy clauses, and impact..."
                  value={discReason}
                  onChange={(e) => setDiscReason(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Mandatory Action Plan / Corrective Requirements</label>
                <textarea
                  rows={3}
                  placeholder="Expected behavior changes, milestone check-ins, or deliverables..."
                  value={discActionPlan}
                  onChange={(e) => setDiscActionPlan(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Effective Date *</label>
                  <input
                    required
                    type="date"
                    value={discEffectiveDate}
                    onChange={(e) => setDiscEffectiveDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Expiry Date (Optional)</label>
                  <input
                    type="date"
                    value={discExpiryDate}
                    onChange={(e) => setDiscExpiryDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 text-xs"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setIsIssuingDisciplinary(false)}
                  className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  disabled={loadingAction}
                  type="submit"
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-medium shadow-sm"
                >
                  {loadingAction ? "Issuing..." : "Issue & Send to Employee"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
