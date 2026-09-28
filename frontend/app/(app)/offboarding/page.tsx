"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const REASON_CATEGORIES = [
  { value: "better_opportunity", label: "Better Opportunity / Career Growth" },
  { value: "relocation", label: "Relocation / Personal Move" },
  { value: "higher_studies", label: "Pursuing Higher Studies" },
  { value: "compensation", label: "Compensation / Financial Growth" },
  { value: "health", label: "Health / Wellness Reasons" },
  { value: "career_change", label: "Career / Industry Change" },
  { value: "other", label: "Other" },
];

const STATUS_COLORS: Record<string, string> = {
  submitted: "bg-blue-100 text-blue-800",
  under_review: "bg-amber-100 text-amber-800",
  approved: "bg-emerald-100 text-emerald-800",
  notice_period: "bg-purple-100 text-purple-800",
  clearance: "bg-indigo-100 text-indigo-800",
  exit_interview: "bg-pink-100 text-pink-800",
  settlement_pending: "bg-orange-100 text-orange-800",
  completed: "bg-slate-900 text-white",
  cancelled: "bg-red-100 text-red-800",
};

export default function EmployeeOffboardingPage() {
  const { data: exitReq, mutate, error } = useSWR("/v3/offboarding/my", fetcher);
  const [activeTab, setActiveTab] = useState<"overview" | "clearance" | "handover" | "interview" | "documents">("overview");

  // Resignation form state
  const [resignationDate, setResignationDate] = useState(new Date().toISOString().split("T")[0]);
  const defaultLwd = new Date();
  defaultLwd.setDate(defaultLwd.getDate() + 30);
  const [proposedLwd, setProposedLwd] = useState(defaultLwd.toISOString().split("T")[0]);
  const [reasonCategory, setReasonCategory] = useState("better_opportunity");
  const [employeeComments, setEmployeeComments] = useState("");

  // Handover state
  const [handoverTitle, setHandoverTitle] = useState("");
  const [handoverDesc, setHandoverDesc] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [docUrl, setDocUrl] = useState("");

  // Interview state
  const [feedbackCompany, setFeedbackCompany] = useState("");
  const [feedbackManagement, setFeedbackManagement] = useState("");
  const [feedbackRole, setFeedbackRole] = useState("");

  const handleSubmitResignation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v3/offboarding/resignations", {
        resignation_date: resignationDate,
        proposed_last_working_day: proposedLwd,
        reason_category: reasonCategory,
        employee_comments: employeeComments,
      });
      alert("Resignation request submitted successfully.");
      mutate();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error submitting resignation");
    }
  };

  const handleAddHandover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!exitReq?.id || !handoverTitle) return;
    try {
      await api.post(`/v3/offboarding/${exitReq.id}/handover`, {
        title: handoverTitle,
        description: handoverDesc,
        recipient_name: recipientName,
        documentation_url: docUrl,
      });
      setHandoverTitle("");
      setHandoverDesc("");
      setRecipientName("");
      setDocUrl("");
      mutate();
    } catch {
      alert("Error adding handover item");
    }
  };

  const handleToggleHandoverStatus = async (handoverId: string, currentStatus: string) => {
    if (!exitReq?.id) return;
    const newStatus = currentStatus === "completed" ? "pending" : "completed";
    try {
      await api.post(`/v3/offboarding/${exitReq.id}/handover-status`, {
        handover_id: handoverId,
        status: newStatus,
      });
      mutate();
    } catch {
      alert("Error updating handover status");
    }
  };

  const handleSubmitInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!exitReq?.id) return;
    try {
      await api.post(`/v3/offboarding/${exitReq.id}/exit-interview`, {
        feedback_company: feedbackCompany,
        feedback_management: feedbackManagement,
        feedback_role: feedbackRole,
        is_completed: true,
      });
      alert("Exit interview feedback submitted securely to HR.");
      mutate();
    } catch {
      alert("Error submitting interview feedback");
    }
  };

  if (!exitReq && !error) {
    return <div className="p-8 text-gray-500 text-sm">Loading offboarding status...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Offboarding & Exit Portal</h2>
        <p className="text-gray-500 text-sm">
          Employee Self-Service: Manage resignation, notice period, clearance, handover, and exit documentation
        </p>
      </div>

      {/* No Exit Request Yet — Show Resignation Form */}
      {(!exitReq || error) && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 max-w-2xl space-y-4">
          <div className="border-b pb-3">
            <h3 className="font-bold text-gray-900 text-base">Submit Formal Resignation</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Initiates your offboarding lifecycle. Your reporting manager and HR will be notified.
            </p>
          </div>

          <form onSubmit={handleSubmitResignation} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-gray-700 mb-1">Resignation Date</label>
                <input
                  type="date"
                  required
                  value={resignationDate}
                  onChange={(e) => setResignationDate(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                />
              </div>
              <div>
                <label className="block font-medium text-gray-700 mb-1">Proposed Last Working Day</label>
                <input
                  type="date"
                  required
                  value={proposedLwd}
                  onChange={(e) => setProposedLwd(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                />
              </div>
            </div>

            <div>
              <label className="block font-medium text-gray-700 mb-1">Reason Category</label>
              <select
                value={reasonCategory}
                onChange={(e) => setReasonCategory(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
              >
                {REASON_CATEGORIES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-medium text-gray-700 mb-1">Comments / Resignation Letter</label>
              <textarea
                rows={5}
                required
                placeholder="State your formal resignation notice, handover commitment, and remarks..."
                value={employeeComments}
                onChange={(e) => setEmployeeComments(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800 leading-relaxed"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-slate-900 hover:bg-black text-white font-medium py-2 rounded-lg transition"
            >
              Submit Resignation Notice
            </button>
          </form>
        </div>
      )}

      {/* Active Exit Request Dashboard */}
      {exitReq && (
        <div className="space-y-6">
          {/* Header Card */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex flex-wrap justify-between items-center gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-indigo-700">{exitReq.ticket_number}</span>
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${STATUS_COLORS[exitReq.status] || "bg-gray-100"}`}>
                  {exitReq.status?.replace("_", " ")}
                </span>
              </div>
              <h3 className="font-bold text-lg text-gray-900 mt-1">Exit Case Overview</h3>
              <p className="text-xs text-gray-500">
                Notice Period: {exitReq.notice_period_days} Days • Resigned: {exitReq.resignation_date}
              </p>
            </div>

            <div className="flex gap-4 text-xs bg-slate-50 border p-3 rounded-lg">
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Proposed LWD</span>
                <span className="font-semibold text-gray-800">{exitReq.proposed_last_working_day}</span>
              </div>
              <div className="border-l pl-4">
                <span className="text-gray-400 block text-[10px] uppercase">Approved LWD</span>
                <span className="font-bold text-indigo-700">{exitReq.approved_last_working_day || "Pending Approval"}</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-gray-200">
            {[
              { id: "overview", label: "📌 Overview & Notice" },
              { id: "clearance", label: "✅ Departmental Clearance" },
              { id: "handover", label: "🤝 Knowledge Handover" },
              { id: "interview", label: "💬 Exit Interview" },
              { id: "documents", label: "📄 Relieving & Exit Docs" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
                  activeTab === tab.id
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab 1: Overview */}
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-3 text-xs">
                <h4 className="font-bold text-gray-900">Your Resignation Statement</h4>
                <div className="bg-gray-50 p-3 rounded-lg border text-gray-700 leading-relaxed">
                  {exitReq.employee_comments}
                </div>
                <div className="text-gray-500">
                  <span className="font-medium text-gray-700">Reason Category:</span>{" "}
                  <span className="capitalize">{exitReq.reason_category?.replace("_", " ")}</span>
                </div>
              </div>

              <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4 text-xs">
                <h4 className="font-bold text-gray-900">Review & Leadership Acknowledgements</h4>
                <div className="space-y-3">
                  <div className="border p-3 rounded-lg">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-semibold text-gray-800">Manager Review</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${exitReq.manager_approved_at ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-600"}`}>
                        {exitReq.manager_approved_at ? "Acknowledged" : "Pending"}
                      </span>
                    </div>
                    <p className="text-gray-600 text-[11px]">{exitReq.manager_comments || "No comments from manager yet."}</p>
                  </div>

                  <div className="border p-3 rounded-lg">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-semibold text-gray-800">HR Final Approval</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${exitReq.hr_approved_at ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-600"}`}>
                        {exitReq.hr_approved_at ? "Approved" : "Pending"}
                      </span>
                    </div>
                    <p className="text-gray-600 text-[11px]">{exitReq.hr_comments || "Pending HR review."}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Clearance Status */}
          {activeTab === "clearance" && (
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
              <h4 className="font-bold text-gray-900 text-sm">Departmental Signoff & Asset Returns</h4>
              <p className="text-xs text-gray-500">
                All departments must sign off on equipment, access, and finance clearance prior to final settlement.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {(exitReq.clearance_tasks || []).map((t: any) => (
                  <div key={t.id} className="p-4 border rounded-xl bg-gray-50 space-y-1.5 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="font-bold uppercase tracking-wider text-[10px] text-gray-500">{t.department}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${t.is_cleared ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                        {t.is_cleared ? "Cleared" : "Pending Clearance"}
                      </span>
                    </div>
                    <h5 className="font-semibold text-gray-800 text-sm">{t.task_name}</h5>
                    {t.remarks && <p className="text-[11px] text-gray-600">Note: {t.remarks}</p>}
                    {t.cleared_at && (
                      <p className="text-[10px] text-gray-400">Signed off: {new Date(t.cleared_at).toLocaleDateString()}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab 3: Knowledge Handover */}
          {activeTab === "handover" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <div className="lg:col-span-5 bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-3">
                <h4 className="font-bold text-gray-900 text-sm">Log Knowledge Handover</h4>
                <form onSubmit={handleAddHandover} className="space-y-3 text-xs">
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Handover Item / Task</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Auth Service Runbook & Deployment Secrets"
                      value={handoverTitle}
                      onChange={(e) => setHandoverTitle(e.target.value)}
                      className="w-full border rounded-lg px-3 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Recipient Peer / Lead</label>
                    <input
                      type="text"
                      placeholder="Name of recipient teammate"
                      value={recipientName}
                      onChange={(e) => setRecipientName(e.target.value)}
                      className="w-full border rounded-lg px-3 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Documentation URL / Link</label>
                    <input
                      type="url"
                      placeholder="https://..."
                      value={docUrl}
                      onChange={(e) => setDocUrl(e.target.value)}
                      className="w-full border rounded-lg px-3 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Description & Handover Notes</label>
                    <textarea
                      rows={3}
                      placeholder="Detailed context, credentials handover, repo links..."
                      value={handoverDesc}
                      onChange={(e) => setHandoverDesc(e.target.value)}
                      className="w-full border rounded-lg px-3 py-1.5 text-xs"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-1.5 rounded-lg transition"
                  >
                    Add Handover Record
                  </button>
                </form>
              </div>

              <div className="lg:col-span-7 bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-3">
                <h4 className="font-bold text-gray-900 text-sm">Handover Checklist</h4>
                <div className="space-y-2">
                  {(exitReq.handovers || []).map((h: any) => (
                    <div key={h.id} className="p-3.5 border rounded-lg bg-gray-50 flex justify-between items-start text-xs">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${h.status === "completed" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                            {h.status}
                          </span>
                          <h5 className="font-semibold text-gray-800">{h.title}</h5>
                        </div>
                        {h.description && <p className="text-gray-600 text-[11px]">{h.description}</p>}
                        {h.recipient_name && <p className="text-gray-500 text-[11px]">Recipient: {h.recipient_name}</p>}
                        {h.documentation_url && (
                          <a href={h.documentation_url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline text-[11px] block">
                            🔗 View Handover Docs
                          </a>
                        )}
                      </div>
                      <button
                        onClick={() => handleToggleHandoverStatus(h.id, h.status)}
                        className="text-xs bg-white border border-gray-300 hover:bg-gray-100 px-2 py-1 rounded"
                      >
                        {h.status === "completed" ? "Mark Pending" : "Mark Done"}
                      </button>
                    </div>
                  ))}
                  {(!exitReq.handovers || exitReq.handovers.length === 0) && (
                    <p className="text-xs text-gray-400 py-4 text-center">No handover items logged yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tab 4: Exit Interview */}
          {activeTab === "interview" && (
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm max-w-2xl space-y-4">
              <div>
                <h4 className="font-bold text-gray-900 text-base">Confidential Exit Interview</h4>
                <p className="text-xs text-gray-500">
                  Your feedback helps Zeramai improve culture and operations. Feedback is confidential to HR leadership.
                </p>
              </div>

              {exitReq.interview?.is_completed ? (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 space-y-1">
                  <p className="font-bold">✅ Exit Interview Submitted</p>
                  <p>Completed on {new Date(exitReq.interview.completed_at).toLocaleDateString()}. Thank you for your feedback.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmitInterview} className="space-y-4 text-xs">
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Company Culture & Work Environment</label>
                    <textarea
                      rows={3}
                      placeholder="What did you appreciate? What could be improved?"
                      value={feedbackCompany}
                      onChange={(e) => setFeedbackCompany(e.target.value)}
                      className="w-full border rounded-lg p-2.5 text-xs text-gray-800"
                    />
                  </div>

                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Management & Leadership Support</label>
                    <textarea
                      rows={3}
                      placeholder="Feedback regarding team leadership, communication, and direction..."
                      value={feedbackManagement}
                      onChange={(e) => setFeedbackManagement(e.target.value)}
                      className="w-full border rounded-lg p-2.5 text-xs text-gray-800"
                    />
                  </div>

                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Job Role & Growth Opportunities</label>
                    <textarea
                      rows={3}
                      placeholder="Were expectations clear? Did you have room to develop?"
                      value={feedbackRole}
                      onChange={(e) => setFeedbackRole(e.target.value)}
                      className="w-full border rounded-lg p-2.5 text-xs text-gray-800"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition"
                  >
                    Submit Confidential Feedback
                  </button>
                </form>
              )}
            </div>
          )}

          {/* Tab 5: Exit Documents */}
          {activeTab === "documents" && (
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4 text-xs">
              <h4 className="font-bold text-gray-900 text-sm">Exit & Relieving Documentation</h4>
              <p className="text-gray-500">
                Official documents generated upon approval of your exit and final clearance.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="border p-4 rounded-xl bg-gray-50 space-y-2">
                  <span className="text-lg">📜</span>
                  <h5 className="font-bold text-gray-800">Resignation Acceptance</h5>
                  <p className="text-[11px] text-gray-500">Official acknowledgement of notice period and approved LWD.</p>
                  <button className="text-indigo-600 hover:underline font-semibold text-[11px]">
                    Download Acceptance Letter
                  </button>
                </div>

                <div className="border p-4 rounded-xl bg-gray-50 space-y-2">
                  <span className="text-lg">📄</span>
                  <h5 className="font-bold text-gray-800">Relieving Letter</h5>
                  <p className="text-[11px] text-gray-500">Released once all departmental clearances are complete.</p>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${exitReq.status === "completed" ? "bg-emerald-100 text-emerald-800" : "bg-gray-200 text-gray-600"}`}>
                    {exitReq.status === "completed" ? "Ready" : "Pending Completion"}
                  </span>
                </div>

                <div className="border p-4 rounded-xl bg-gray-50 space-y-2">
                  <span className="text-lg">🏆</span>
                  <h5 className="font-bold text-gray-800">Experience Certificate</h5>
                  <p className="text-[11px] text-gray-500">Service tenure and designation record for future employers.</p>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${exitReq.status === "completed" ? "bg-emerald-100 text-emerald-800" : "bg-gray-200 text-gray-600"}`}>
                    {exitReq.status === "completed" ? "Ready" : "Pending Completion"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
