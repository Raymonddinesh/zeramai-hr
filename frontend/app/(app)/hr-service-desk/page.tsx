"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const CATEGORIES = [
  { value: "payroll", label: "Payroll" },
  { value: "leave", label: "Leave" },
  { value: "attendance", label: "Attendance" },
  { value: "benefits", label: "Benefits" },
  { value: "documents", label: "Documents" },
  { value: "employment_verification", label: "Employment Verification" },
  { value: "onboarding", label: "Onboarding" },
  { value: "offboarding", label: "Offboarding" },
  { value: "it_access", label: "IT / Access" },
  { value: "policy", label: "Policy" },
  { value: "general_hr", label: "General HR" },
];

const PRIORITIES = [
  { value: "low", label: "Low", color: "bg-gray-100 text-gray-700" },
  { value: "medium", label: "Medium", color: "bg-blue-100 text-blue-700" },
  { value: "high", label: "High", color: "bg-orange-100 text-orange-700" },
  { value: "urgent", label: "Urgent", color: "bg-red-100 text-red-700" },
];

const STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "assigned", label: "Assigned" },
  { value: "in_progress", label: "In Progress" },
  { value: "waiting_for_employee", label: "Waiting for Employee" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

const STATUS_COLORS: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  assigned: "bg-indigo-100 text-indigo-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  waiting_for_employee: "bg-amber-100 text-amber-800",
  resolved: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-600",
};

export default function HRServiceDeskPage() {
  const { user } = useAuth();
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Resolution & Comment state
  const [resolutionText, setResolutionText] = useState("");
  const [commentText, setCommentText] = useState("");
  const [isInternalComment, setIsInternalComment] = useState(true);
  const [assigneeId, setAssigneeId] = useState("");

  const queryParams = new URLSearchParams();
  if (statusFilter) queryParams.append("status_filter", statusFilter);
  if (categoryFilter) queryParams.append("category_filter", categoryFilter);
  if (priorityFilter) queryParams.append("priority_filter", priorityFilter);

  const url = `/v3/hr-requests${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;
  const { data: requests, mutate } = useSWR(url, fetcher);

  const { data: detail, mutate: mutateDetail } = useSWR(
    selectedId ? `/v3/hr-requests/${selectedId}` : null,
    fetcher
  );

  const filteredRequests = (requests || []).filter((r: any) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.ticket_number?.toLowerCase().includes(q) ||
      r.subject?.toLowerCase().includes(q) ||
      r.description?.toLowerCase().includes(q)
    );
  });

  const handleAssignToMe = async () => {
    if (!selectedId || !user?.id) return;
    try {
      await api.post(`/v3/hr-requests/${selectedId}/assign`, { assigned_to_user_id: user.id });
      mutate();
      mutateDetail();
    } catch {
      alert("Error assigning request");
    }
  };

  const handleCustomAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !assigneeId) return;
    try {
      await api.post(`/v3/hr-requests/${selectedId}/assign`, { assigned_to_user_id: assigneeId });
      setAssigneeId("");
      mutate();
      mutateDetail();
    } catch {
      alert("Error assigning request. Please check User ID.");
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!selectedId) return;
    try {
      await api.post(`/v3/hr-requests/${selectedId}/status`, { status: newStatus });
      mutate();
      mutateDetail();
    } catch {
      alert("Error updating status");
    }
  };

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !resolutionText) return;
    try {
      await api.post(`/v3/hr-requests/${selectedId}/resolve`, { resolution: resolutionText });
      setResolutionText("");
      mutate();
      mutateDetail();
    } catch {
      alert("Error resolving request");
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !commentText) return;
    try {
      await api.post(`/v3/hr-requests/${selectedId}/comments`, {
        content: commentText,
        is_internal: isInternalComment,
      });
      setCommentText("");
      mutateDetail();
    } catch {
      alert("Error adding comment");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">HR Service Desk Queue</h2>
          <p className="text-gray-500 text-sm">
            Triage, assign, manage SLA and resolve employee HR support tickets
          </p>
        </div>
        <div className="flex gap-2">
          <span className="text-xs bg-indigo-50 text-indigo-700 font-semibold px-3 py-1.5 rounded-lg border border-indigo-200">
            {filteredRequests.length} Tickets in Queue
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div>
          <label className="block text-gray-600 font-medium mb-1">Search</label>
          <input
            type="text"
            placeholder="Search ticket #, subject..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full border rounded-lg px-3 py-1.5 text-xs text-gray-800"
          />
        </div>

        <div>
          <label className="block text-gray-600 font-medium mb-1">Status</label>
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

        <div>
          <label className="block text-gray-600 font-medium mb-1">Category</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-full border rounded-lg px-3 py-1.5 text-xs text-gray-800"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-gray-600 font-medium mb-1">Priority</label>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="w-full border rounded-lg px-3 py-1.5 text-xs text-gray-800"
          >
            <option value="">All Priorities</option>
            {PRIORITIES.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Queue and Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Ticket List */}
        <div className={selectedId ? "lg:col-span-5 space-y-3" : "lg:col-span-12 space-y-3"}>
          {filteredRequests.map((r: any) => {
            const isSelected = selectedId === r.id;
            return (
              <div
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={`p-4 rounded-xl border transition cursor-pointer shadow-sm ${
                  isSelected
                    ? "bg-indigo-50/60 border-indigo-500 ring-1 ring-indigo-500"
                    : "bg-white border-gray-200 hover:border-indigo-300"
                }`}
              >
                <div className="flex justify-between items-start mb-1.5">
                  <span className="font-mono text-xs font-bold text-indigo-700">{r.ticket_number}</span>
                  <div className="flex gap-1.5">
                    <span
                      className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                        PRIORITIES.find((p) => p.value === r.priority)?.color || "bg-gray-100"
                      }`}
                    >
                      {r.priority}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                        STATUS_COLORS[r.status] || "bg-gray-100"
                      }`}
                    >
                      {r.status?.replace("_", " ")}
                    </span>
                  </div>
                </div>

                <h4 className="font-semibold text-sm text-gray-900 line-clamp-1">{r.subject}</h4>
                <p className="text-xs text-gray-500 line-clamp-2 mt-1">{r.description}</p>

                <div className="flex justify-between items-center text-[11px] text-gray-400 mt-3 pt-2 border-t border-gray-100">
                  <span className="capitalize">{r.category?.replace("_", " ")}</span>
                  <span>{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}

          {filteredRequests.length === 0 && (
            <div className="bg-white p-8 rounded-xl border border-gray-200 text-center text-gray-400 text-sm">
              No support tickets found matching the selected filters.
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
                  <span
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                      STATUS_COLORS[detail.status] || "bg-gray-100"
                    }`}
                  >
                    {detail.status?.replace("_", " ")}
                  </span>
                </div>
                <h3 className="font-bold text-xl text-gray-900 mt-1">{detail.subject}</h3>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕ Close
              </button>
            </div>

            {/* Meta info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs bg-gray-50 p-3 rounded-lg border border-gray-100">
              <div>
                <span className="text-gray-500 block">Category</span>
                <span className="font-semibold text-gray-800 capitalize">{detail.category?.replace("_", " ")}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Priority</span>
                <span className="font-semibold text-gray-800 uppercase">{detail.priority}</span>
              </div>
              <div>
                <span className="text-gray-500 block">Assigned To</span>
                <span className="font-semibold text-gray-800">
                  {detail.assigned_to_user_id ? "Assigned" : "Unassigned"}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block">Created</span>
                <span className="font-semibold text-gray-800">{new Date(detail.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            {/* Description */}
            <div>
              <h4 className="font-semibold text-xs text-gray-500 uppercase tracking-wider mb-1">Description</h4>
              <p className="text-xs text-gray-800 bg-white p-3 rounded-lg border leading-relaxed">
                {detail.description}
              </p>
            </div>

            {/* Resolution if present */}
            {detail.resolution && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 leading-relaxed">
                <span className="font-bold">Official Resolution:</span> {detail.resolution}
              </div>
            )}

            {/* Actions: Assignment & Status */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t text-xs">
              {/* Assignment */}
              <div className="space-y-2">
                <h4 className="font-semibold text-gray-800">Assign Ticket</h4>
                <div className="flex gap-2">
                  <button
                    onClick={handleAssignToMe}
                    className="bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-medium px-3 py-1.5 rounded-lg border border-indigo-200 transition"
                  >
                    Assign to Me
                  </button>
                </div>
                <form onSubmit={handleCustomAssign} className="flex gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="User ID..."
                    value={assigneeId}
                    onChange={(e) => setAssigneeId(e.target.value)}
                    className="border rounded-lg px-2 py-1 text-xs w-full"
                  />
                  <button
                    type="submit"
                    className="bg-gray-800 hover:bg-black text-white px-3 py-1 rounded-lg text-xs"
                  >
                    Assign
                  </button>
                </form>
              </div>

              {/* Status Update */}
              <div className="space-y-2">
                <h4 className="font-semibold text-gray-800">Lifecycle Status</h4>
                <div className="flex flex-wrap gap-1.5">
                  {STATUS_OPTIONS.map((s) => (
                    <button
                      key={s.value}
                      onClick={() => handleStatusChange(s.value)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition ${
                        detail.status === s.value
                          ? "bg-slate-900 text-white font-bold"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Resolve Form */}
            {detail.status !== "resolved" && detail.status !== "closed" && (
              <form onSubmit={handleResolve} className="space-y-2 pt-2 border-t text-xs">
                <h4 className="font-semibold text-gray-800">Resolve Request</h4>
                <textarea
                  rows={2}
                  required
                  placeholder="Enter clear resolution details for the employee..."
                  value={resolutionText}
                  onChange={(e) => setResolutionText(e.target.value)}
                  className="w-full border rounded-lg p-2 text-xs text-gray-800"
                />
                <button
                  type="submit"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-1.5 rounded-lg transition"
                >
                  Mark as Resolved
                </button>
              </form>
            )}

            {/* Comments & Internal Notes */}
            <div className="space-y-3 pt-2 border-t">
              <h4 className="font-semibold text-sm text-gray-800">Timeline & Comments</h4>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {(detail.comments || []).map((c: any) => (
                  <div
                    key={c.id}
                    className={`p-3 rounded-lg text-xs ${
                      c.is_internal
                        ? "bg-amber-50/80 border border-amber-200"
                        : "bg-gray-50 border border-gray-200"
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium text-gray-700">User ID: {c.author_user_id}</span>
                      <div className="flex items-center gap-1.5">
                        {c.is_internal && (
                          <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 bg-amber-200 text-amber-900 rounded">
                            Internal Note (Hidden from Employee)
                          </span>
                        )}
                        <span className="text-[10px] text-gray-400">
                          {new Date(c.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                    <p className="text-gray-800">{c.content}</p>
                  </div>
                ))}

                {(!detail.comments || detail.comments.length === 0) && (
                  <p className="text-xs text-gray-400 text-center py-2">No comments or activity yet.</p>
                )}
              </div>

              {/* Add comment / note */}
              <form onSubmit={handleAddComment} className="space-y-2 pt-2 text-xs">
                <input
                  type="text"
                  required
                  placeholder="Add note or response..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                />
                <div className="flex justify-between items-center">
                  <label className="flex items-center gap-1.5 text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isInternalComment}
                      onChange={(e) => setIsInternalComment(e.target.checked)}
                      className="rounded text-amber-600"
                    />
                    <span className="font-medium text-amber-800">
                      🔒 Mark as Internal HR Note (Invisible to Employee)
                    </span>
                  </label>
                  <button
                    type="submit"
                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-1.5 rounded-lg transition"
                  >
                    Post Note
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
