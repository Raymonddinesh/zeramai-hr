"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const STATUS_OPTIONS = [
  { value: "submitted", label: "Submitted" },
  { value: "under_review", label: "Under Review" },
  { value: "approved", label: "Approved" },
  { value: "notice_period", label: "Notice Period" },
  { value: "clearance", label: "Clearance Pending" },
  { value: "settlement_pending", label: "Settlement Pending" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
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

export default function OffboardingAdminPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Review state
  const [reviewAction, setReviewAction] = useState<"approve" | "reject" | "under_review">("approve");
  const [reviewComments, setReviewComments] = useState("");
  const [approvedLwd, setApprovedLwd] = useState("");

  // Settlement state
  const [settlementAmount, setSettlementAmount] = useState("");
  const [leaveEncashmentDays, setLeaveEncashmentDays] = useState("");
  const [settlementStatus, setSettlementStatus] = useState("approved");
  const [settlementRemarks, setSettlementRemarks] = useState("");

  const url = `/v3/offboarding${statusFilter ? `?status_filter=${statusFilter}` : ""}`;
  const { data: exits, mutate } = useSWR(url, fetcher);

  const { data: detail, mutate: mutateDetail } = useSWR(
    selectedId ? `/v3/offboarding/${selectedId}` : null,
    fetcher
  );

  const filteredExits = (exits || []).filter((e: any) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      e.ticket_number?.toLowerCase().includes(q) ||
      e.employee_comments?.toLowerCase().includes(q) ||
      e.reason_category?.toLowerCase().includes(q)
    );
  });

  const handleReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    try {
      await api.post(`/v3/offboarding/${selectedId}/review`, {
        action: reviewAction,
        comments: reviewComments,
        approved_last_working_day: approvedLwd || undefined,
      });
      alert(`Exit request updated: ${reviewAction}`);
      setReviewComments("");
      mutate();
      mutateDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error reviewing exit request");
    }
  };

  const handleClearTask = async (taskId: string, isCleared: boolean) => {
    if (!selectedId) return;
    try {
      await api.post(`/v3/offboarding/${selectedId}/clearance`, {
        task_id: taskId,
        is_cleared: !isCleared,
        remarks: !isCleared ? "Cleared by HR Administrator" : "Clearance revoked",
      });
      mutate();
      mutateDetail();
    } catch {
      alert("Error updating clearance task");
    }
  };

  const handleUpdateSettlement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    try {
      await api.post(`/v3/offboarding/${selectedId}/settlement-readiness`, {
        payroll_reviewed: true,
        leave_balance_reviewed: true,
        asset_clearance_completed: true,
        finance_clearance_completed: true,
        leave_encashment_days: leaveEncashmentDays ? parseFloat(leaveEncashmentDays) : 0,
        settlement_amount: settlementAmount ? parseFloat(settlementAmount) : undefined,
        settlement_status: settlementStatus,
        remarks: settlementRemarks,
      });
      alert("Settlement readiness updated.");
      mutate();
      mutateDetail();
    } catch {
      alert("Error updating settlement");
    }
  };

  const handleCompleteExit = async () => {
    if (!selectedId) return;
    if (!confirm("Are you sure you want to finalize offboarding? This will complete employment closure and update history.")) return;
    try {
      await api.post(`/v3/offboarding/${selectedId}/complete`);
      alert("Offboarding finalized and employment closure completed!");
      mutate();
      mutateDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error completing exit");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Offboarding & Exit Administration</h2>
          <p className="text-gray-500 text-sm">
            Monitor resignation pipeline, conduct reviews, oversee clearance, interview feedback & settlement readiness
          </p>
        </div>
        <span className="text-xs bg-indigo-50 text-indigo-700 font-semibold px-3 py-1.5 rounded-lg border border-indigo-200">
          {filteredExits.length} Active Exit Cases
        </span>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-wrap gap-4 text-xs">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search ticket #, reason, comments..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full border rounded-lg px-3 py-1.5 text-xs text-gray-800"
          />
        </div>

        <div className="w-56">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full border rounded-lg px-3 py-1.5 text-xs text-gray-800"
          >
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Pipeline and Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Pipeline List */}
        <div className={selectedId ? "lg:col-span-5 space-y-3" : "lg:col-span-12 space-y-3"}>
          {filteredExits.map((e: any) => {
            const isSelected = selectedId === e.id;
            return (
              <div
                key={e.id}
                onClick={() => setSelectedId(e.id)}
                className={`p-4 rounded-xl border transition cursor-pointer shadow-sm ${
                  isSelected
                    ? "bg-indigo-50/60 border-indigo-500 ring-1 ring-indigo-500"
                    : "bg-white border-gray-200 hover:border-indigo-300"
                }`}
              >
                <div className="flex justify-between items-start mb-1.5">
                  <span className="font-mono text-xs font-bold text-indigo-700">{e.ticket_number}</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${STATUS_COLORS[e.status] || "bg-gray-100"}`}>
                    {e.status?.replace("_", " ")}
                  </span>
                </div>

                <p className="text-xs font-semibold text-gray-800 line-clamp-1">{e.employee_comments || "Resignation submitted"}</p>

                <div className="flex justify-between items-center text-[11px] text-gray-500 mt-3 pt-2 border-t border-gray-100">
                  <span className="capitalize">{e.reason_category?.replace("_", " ")}</span>
                  <span>LWD: <strong className="text-indigo-700">{e.approved_last_working_day || e.proposed_last_working_day}</strong></span>
                </div>
              </div>
            );
          })}

          {filteredExits.length === 0 && (
            <div className="bg-white p-8 rounded-xl border border-gray-200 text-center text-gray-400 text-sm">
              No exit cases matching criteria.
            </div>
          )}
        </div>

        {/* Selected Detail Panel */}
        {selectedId && detail && (
          <div className="lg:col-span-7 bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-6">
            <div className="flex justify-between items-start border-b pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-indigo-700">{detail.ticket_number}</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${STATUS_COLORS[detail.status] || "bg-gray-100"}`}>
                    {detail.status?.replace("_", " ")}
                  </span>
                </div>
                <h3 className="font-bold text-lg text-gray-900 mt-1">Exit Case Management</h3>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕ Close
              </button>
            </div>

            {/* Overview Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-gray-50 p-3 rounded-lg border">
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Resigned</span>
                <span className="font-semibold text-gray-800">{detail.resignation_date}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Notice Period</span>
                <span className="font-semibold text-gray-800">{detail.notice_period_days} Days</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Proposed LWD</span>
                <span className="font-semibold text-gray-800">{detail.proposed_last_working_day}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Approved LWD</span>
                <span className="font-bold text-indigo-700">{detail.approved_last_working_day || "Pending"}</span>
              </div>
            </div>

            {/* Employee Resignation Letter */}
            <div className="text-xs space-y-1">
              <h4 className="font-semibold text-gray-700">Resignation Statement:</h4>
              <p className="bg-slate-50 p-3 rounded-lg border text-gray-700 leading-relaxed">
                {detail.employee_comments}
              </p>
            </div>

            {/* Section 1: Review & Approval */}
            {detail.status !== "completed" && detail.status !== "cancelled" && (
              <form onSubmit={handleReview} className="space-y-3 pt-3 border-t text-xs">
                <h4 className="font-bold text-gray-900 text-sm">Leadership Review & LWD Decision</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Decision</label>
                    <select
                      value={reviewAction}
                      onChange={(e) => setReviewAction(e.target.value as any)}
                      className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                    >
                      <option value="approve">Approve & Start Notice Period</option>
                      <option value="under_review">Mark Under Review</option>
                      <option value="reject">Reject / Cancel Resignation</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Approved Last Working Day</label>
                    <input
                      type="date"
                      value={approvedLwd}
                      onChange={(e) => setApprovedLwd(e.target.value)}
                      className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Review Comments</label>
                  <input
                    type="text"
                    placeholder="Leadership remarks, early release terms, etc..."
                    value={reviewComments}
                    onChange={(e) => setReviewComments(e.target.value)}
                    className="w-full border rounded-lg px-3 py-1.5 text-xs"
                  />
                </div>
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-1.5 rounded-lg transition text-xs"
                >
                  Record Review Decision
                </button>
              </form>
            )}

            {/* Section 2: Departmental Clearance Checklist */}
            <div className="space-y-2 pt-3 border-t text-xs">
              <h4 className="font-bold text-gray-900 text-sm">Departmental Signoff & Asset Returns</h4>
              <div className="space-y-2">
                {(detail.clearance_tasks || []).map((t: any) => (
                  <div key={t.id} className="p-3 border rounded-lg bg-gray-50 flex justify-between items-center">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold uppercase text-[9px] px-1.5 py-0.5 rounded bg-white border text-gray-600">{t.department}</span>
                        <span className="font-semibold text-gray-800">{t.task_name}</span>
                      </div>
                      {t.remarks && <p className="text-[10px] text-gray-500 mt-0.5">{t.remarks}</p>}
                    </div>
                    <button
                      onClick={() => handleClearTask(t.id, t.is_cleared)}
                      className={`px-3 py-1 rounded text-xs font-semibold transition ${
                        t.is_cleared
                          ? "bg-emerald-600 text-white hover:bg-emerald-700"
                          : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      {t.is_cleared ? "✓ Cleared" : "Sign Off"}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 3: Exit Interview Feedback */}
            {detail.interview && (
              <div className="space-y-2 pt-3 border-t text-xs">
                <h4 className="font-bold text-gray-900 text-sm">Exit Interview Responses</h4>
                <div className="p-3.5 bg-slate-50 border rounded-lg space-y-2">
                  <div className="flex justify-between">
                    <span className="font-semibold text-gray-700">Status: {detail.interview.is_completed ? "Completed" : "Pending Employee Submission"}</span>
                    {detail.interview.primary_reason && <span className="capitalize text-indigo-700 font-bold">{detail.interview.primary_reason?.replace("_", " ")}</span>}
                  </div>
                  {detail.interview.feedback_company && (
                    <div>
                      <span className="font-medium text-gray-500 block text-[10px]">Culture & Company:</span>
                      <p className="text-gray-800">{detail.interview.feedback_company}</p>
                    </div>
                  )}
                  {detail.interview.feedback_management && (
                    <div>
                      <span className="font-medium text-gray-500 block text-[10px]">Management & Direction:</span>
                      <p className="text-gray-800">{detail.interview.feedback_management}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Section 4: Settlement Readiness Checklist */}
            {detail.settlement && (
              <form onSubmit={handleUpdateSettlement} className="space-y-3 pt-3 border-t text-xs">
                <h4 className="font-bold text-gray-900 text-sm">Final Settlement (FnF) Readiness</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Leave Encashment (Days)</label>
                    <input
                      type="number"
                      step="0.5"
                      placeholder="e.g. 5"
                      value={leaveEncashmentDays}
                      onChange={(e) => setLeaveEncashmentDays(e.target.value)}
                      className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Settlement Net Payable (INR)</label>
                    <input
                      type="number"
                      step="1"
                      placeholder="e.g. 45000"
                      value={settlementAmount}
                      onChange={(e) => setSettlementAmount(e.target.value)}
                      className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-700 font-medium mb-1">Settlement Status</label>
                    <select
                      value={settlementStatus}
                      onChange={(e) => setSettlementStatus(e.target.value)}
                      className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                    >
                      <option value="pending">Pending</option>
                      <option value="in_review">In Review</option>
                      <option value="approved">Approved</option>
                      <option value="processed">Processed</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-gray-700 font-medium mb-1">Payroll & Finance Remarks</label>
                  <input
                    type="text"
                    placeholder="FnF statement calculation notes..."
                    value={settlementRemarks}
                    onChange={(e) => setSettlementRemarks(e.target.value)}
                    className="w-full border rounded-lg px-3 py-1.5 text-xs"
                  />
                </div>

                <button
                  type="submit"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-1.5 rounded-lg transition text-xs"
                >
                  Save Settlement Checklist
                </button>
              </form>
            )}

            {/* Section 5: Final Employment Closure */}
            {detail.status !== "completed" && (
              <div className="pt-4 border-t">
                <button
                  onClick={handleCompleteExit}
                  className="w-full bg-slate-900 hover:bg-black text-white font-bold py-2.5 rounded-xl transition text-xs flex justify-center items-center gap-2 shadow-sm"
                >
                  🏁 Finalize Offboarding & Close Employment Record
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
