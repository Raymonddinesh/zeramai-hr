"use client";

import useSWR from "swr";
import api from "@/lib/api";
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

const STATUS_COLORS: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  assigned: "bg-indigo-100 text-indigo-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  waiting_for_employee: "bg-amber-100 text-amber-800",
  resolved: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-600",
};

export default function HRRequestsPage() {
  const { data: requests, mutate } = useSWR("/v3/hr-requests", fetcher);
  const [activeTab, setActiveTab] = useState<"list" | "create" | "detail">("list");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Create form state
  const [category, setCategory] = useState("general_hr");
  const [priority, setPriority] = useState("medium");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [comment, setComment] = useState("");

  const { data: detail, mutate: mutateDetail } = useSWR(
    selectedId ? `/v3/hr-requests/${selectedId}` : null,
    fetcher
  );

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject || !description) return;
    try {
      await api.post("/v3/hr-requests", { category, priority, subject, description });
      alert("HR request submitted successfully!");
      setSubject("");
      setDescription("");
      setActiveTab("list");
      mutate();
    } catch {
      alert("Error creating request");
    }
  };

  const handleAddComment = async () => {
    if (!comment || !selectedId) return;
    try {
      await api.post(`/v3/hr-requests/${selectedId}/comments`, { content: comment });
      setComment("");
      mutateDetail();
    } catch {
      alert("Error adding comment");
    }
  };

  const handleCloseRequest = async () => {
    if (!selectedId) return;
    try {
      await api.post(`/v3/hr-requests/${selectedId}/status`, { status: "closed" });
      mutateDetail();
      mutate();
    } catch {
      alert("Cannot close request — it may not be in resolved status.");
    }
  };

  const openDetail = (id: string) => {
    setSelectedId(id);
    setActiveTab("detail");
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">My HR Requests</h2>
        <p className="text-gray-500 text-sm">Raise and track your HR support requests</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("list")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "list"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          📋 My Requests
        </button>
        <button
          onClick={() => setActiveTab("create")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "create"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          ➕ New Request
        </button>
        {selectedId && (
          <button
            onClick={() => setActiveTab("detail")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === "detail"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            🔍 Request Detail
          </button>
        )}
      </div>

      {/* List */}
      {activeTab === "list" && (
        <div className="space-y-3">
          {(requests || []).map((r: any) => (
            <div
              key={r.id}
              onClick={() => openDetail(r.id)}
              className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm cursor-pointer hover:border-indigo-300 transition"
            >
              <div className="flex justify-between items-center mb-2">
                <span className="font-mono text-xs font-bold text-indigo-700">{r.ticket_number}</span>
                <div className="flex gap-2">
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    PRIORITIES.find(p => p.value === r.priority)?.color || "bg-gray-100"
                  }`}>
                    {r.priority}
                  </span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    STATUS_COLORS[r.status] || "bg-gray-100"
                  }`}>
                    {r.status?.replace("_", " ")}
                  </span>
                </div>
              </div>
              <h4 className="font-semibold text-sm text-gray-900">{r.subject}</h4>
              <p className="text-xs text-gray-500 mt-1">
                Category: <span className="capitalize">{r.category?.replace("_", " ")}</span> •
                Created: {new Date(r.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
          {(!requests || requests.length === 0) && (
            <p className="text-sm text-gray-400 py-8 text-center">No HR requests yet. Create one to get started.</p>
          )}
        </div>
      )}

      {/* Create */}
      {activeTab === "create" && (
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm max-w-2xl">
          <h3 className="font-semibold text-gray-800 mb-4">Submit HR Request</h3>
          <form onSubmit={handleCreate} className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                >
                  {CATEGORIES.map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block font-medium text-gray-700 mb-1">Priority</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
                >
                  {PRIORITIES.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block font-medium text-gray-700 mb-1">Subject</label>
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Brief summary of your request"
                className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
              />
            </div>
            <div>
              <label className="block font-medium text-gray-700 mb-1">Description</label>
              <textarea
                rows={4}
                required
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Provide details about your HR request..."
                className="w-full border rounded-lg px-3 py-2 text-xs text-gray-800"
              />
            </div>
            <button
              type="submit"
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition"
            >
              Submit Request
            </button>
          </form>
        </div>
      )}

      {/* Detail */}
      {activeTab === "detail" && detail && (
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm max-w-3xl space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <span className="font-mono text-sm font-bold text-indigo-700">{detail.ticket_number}</span>
              <h3 className="font-bold text-lg text-gray-900 mt-1">{detail.subject}</h3>
            </div>
            <div className="flex gap-2">
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                PRIORITIES.find(p => p.value === detail.priority)?.color || "bg-gray-100"
              }`}>
                {detail.priority}
              </span>
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                STATUS_COLORS[detail.status] || "bg-gray-100"
              }`}>
                {detail.status?.replace("_", " ")}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs text-gray-600">
            <p>Category: <span className="capitalize font-medium text-gray-800">{detail.category?.replace("_", " ")}</span></p>
            <p>Created: <span className="font-medium text-gray-800">{new Date(detail.created_at).toLocaleString()}</span></p>
            {detail.resolved_at && <p>Resolved: <span className="font-medium text-gray-800">{new Date(detail.resolved_at).toLocaleString()}</span></p>}
            {detail.closed_at && <p>Closed: <span className="font-medium text-gray-800">{new Date(detail.closed_at).toLocaleString()}</span></p>}
          </div>

          <div className="p-3 bg-gray-50 rounded-lg text-xs text-gray-700 leading-relaxed">
            {detail.description}
          </div>

          {detail.resolution && (
            <div className="p-3 bg-green-50 rounded-lg text-xs text-green-800 leading-relaxed">
              <span className="font-bold">Resolution:</span> {detail.resolution}
            </div>
          )}

          {/* Comments */}
          <div className="space-y-2">
            <h4 className="font-semibold text-sm text-gray-800">Comments</h4>
            {(detail.comments || []).map((c: any) => (
              <div key={c.id} className={`p-3 rounded-lg text-xs ${c.is_internal ? "bg-amber-50 border border-amber-200" : "bg-gray-50 border border-gray-200"}`}>
                <p className="text-gray-700">{c.content}</p>
                <p className="text-[10px] text-gray-400 mt-1">
                  {new Date(c.created_at).toLocaleString()}
                  {c.is_internal && <span className="ml-2 text-amber-600 font-bold">INTERNAL</span>}
                </p>
              </div>
            ))}
          </div>

          {/* Add comment */}
          {detail.status !== "closed" && (
            <div className="flex gap-2">
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment..."
                className="flex-1 border rounded-lg px-3 py-2 text-xs text-gray-800"
              />
              <button
                onClick={handleAddComment}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-4 py-2 rounded-lg transition"
              >
                Send
              </button>
            </div>
          )}

          {/* Close button for resolved requests */}
          {detail.status === "resolved" && (
            <button
              onClick={handleCloseRequest}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium py-2 rounded-lg transition"
            >
              ✅ Confirm Resolution & Close Request
            </button>
          )}
        </div>
      )}
    </div>
  );
}
