"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function AdminCommunicationsPage() {
  const [activeTab, setActiveTab] = useState<"broadcasts" | "create" | "templates" | "analytics">("broadcasts");

  // Broadcast Creation Form State
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [announcementType, setAnnouncementType] = useState("GENERAL");
  const [priority, setPriority] = useState("STANDARD");
  const [publishAt, setPublishAt] = useState("");
  const [ackRequired, setAckRequired] = useState(false);
  const [audienceType, setAudienceType] = useState("ALL_EMPLOYEES");
  const [targetDepartment, setTargetDepartment] = useState("");
  const [targetLocation, setTargetLocation] = useState("");
  const [reachEstimate, setReachEstimate] = useState<number | null>(null);
  const [calculatingReach, setCalculatingReach] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Queries
  const { data: announcements, mutate: mutateAnnouncements } = useSWR("/api/v3/communications/announcements", fetcher);
  const { data: templates, mutate: mutateTemplates } = useSWR("/api/v3/communications/templates", fetcher);
  const { data: searchAnalytics } = useSWR("/api/v3/communications/analytics/search", fetcher);

  const calculateReach = async () => {
    setCalculatingReach(true);
    try {
      const payload: any = {
        rules: [
          {
            audience_type: audienceType,
            department_id: targetDepartment || null,
            location_reference: targetLocation || null,
          },
        ],
      };
      const res = await api.post("/api/v3/communications/audience/preview", payload);
      setReachEstimate(res.data.estimated_audience_size);
    } catch {
      setReachEstimate(null);
    } finally {
      setCalculatingReach(false);
    }
  };

  const handleCreateAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !content) {
      alert("Title and content are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: any = {
        title,
        summary,
        content_reference: content,
        announcement_type: announcementType,
        priority,
        publish_at: publishAt ? new Date(publishAt).toISOString() : null,
        acknowledgement_required: ackRequired,
        audience_rules: [
          {
            audience_type: audienceType,
            department_id: targetDepartment || null,
            location_reference: targetLocation || null,
          },
        ],
      };

      await api.post("/api/v3/communications/announcements", payload);
      setStatusMessage("Announcement created successfully!");
      setTitle("");
      setSummary("");
      setContent("");
      setPublishAt("");
      setReachEstimate(null);
      mutateAnnouncements();
      setActiveTab("broadcasts");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Creation failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await api.post(`/api/v3/communications/announcements/${id}/publish`);
      mutateAnnouncements();
      setStatusMessage("Announcement published immediately!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Publish failed");
    }
  };

  const handleCancel = async (id: string) => {
    if (!confirm("Are you sure you want to cancel this announcement?")) return;
    try {
      await api.post(`/api/v3/communications/announcements/${id}/cancel`);
      mutateAnnouncements();
      setStatusMessage("Announcement cancelled.");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Cancellation failed");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📡</span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Enterprise Broadcast & Communications Admin
            </h1>
          </div>
          <p className="text-slate-500 text-xs mt-1">
            Author company broadcasts, configure targeted audience rules, and analyze search governance.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg">
          {(["broadcasts", "create", "templates", "analytics"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition ${
                activeTab === tab
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab === "create" ? "+ New Broadcast" : tab}
            </button>
          ))}
        </div>
      </div>

      {statusMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs p-3 rounded-lg flex items-center justify-between">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="font-bold text-slate-500">×</button>
        </div>
      )}

      {/* Broadcasts Tab */}
      {activeTab === "broadcasts" && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900">Broadcast Campaigns</h2>
            <button
              onClick={() => setActiveTab("create")}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
            >
              + Create Announcement
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {!announcements || announcements.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">No announcements created yet.</div>
            ) : (
              announcements.map((ann: any) => (
                <div key={ann.id} className="p-5 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase">
                        {ann.priority}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          ann.status === "PUBLISHED"
                            ? "bg-emerald-100 text-emerald-800"
                            : ann.status === "SCHEDULED"
                            ? "bg-blue-100 text-blue-800"
                            : ann.status === "CANCELLED"
                            ? "bg-slate-200 text-slate-700"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {ann.status}
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-slate-900">{ann.title}</h3>
                    <p className="text-xs text-slate-500">{ann.summary || "No summary"}</p>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1">
                      <span>Reads: {ann.read_count || 0}</span>
                      <span>•</span>
                      <span>Acks: {ann.acknowledgement_count || 0}</span>
                      <span>•</span>
                      <span>Publish: {new Date(ann.publish_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {ann.status === "DRAFT" || ann.status === "SCHEDULED" ? (
                      <button
                        onClick={() => handlePublish(ann.id)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition"
                      >
                        Publish Now
                      </button>
                    ) : null}
                    {ann.status !== "CANCELLED" && (
                      <button
                        onClick={() => handleCancel(ann.id)}
                        className="bg-slate-100 hover:bg-rose-50 hover:text-rose-600 text-slate-600 text-xs font-medium px-3 py-1.5 rounded-lg transition"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Create Tab */}
      {activeTab === "create" && (
        <form onSubmit={handleCreateAnnouncement} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">Author New Broadcast</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Announcements will be distributed according to audience rules and channel preferences.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Announcement Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Q4 Company All-Hands & Strategy Briefing"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Type</label>
              <select
                value={announcementType}
                onChange={(e) => setAnnouncementType(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="GENERAL">General Notice</option>
                <option value="COMPANY_UPDATE">Company Update</option>
                <option value="POLICY_CHANGE">Policy Change</option>
                <option value="CRITICAL_ALERT">Critical Alert</option>
                <option value="EVENT">Corporate Event</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Priority Level</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="STANDARD">Standard</option>
                <option value="HIGH">High Priority</option>
                <option value="CRITICAL">Critical Alert (Sticky Urgent Banner)</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Scheduled Publish Time (Optional)</label>
              <input
                type="datetime-local"
                value={publishAt}
                onChange={(e) => setPublishAt(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={ackRequired}
                  onChange={(e) => setAckRequired(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-slate-700">
                  Require Employee Acknowledgement
                </span>
              </label>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Summary / Teaser</label>
            <input
              type="text"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Brief 1-2 sentence overview for notifications and lists..."
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Full Broadcast Body *</label>
            <textarea
              required
              rows={6}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Full announcement details, links, instructions, and dates..."
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-sans"
            />
          </div>

          {/* Audience Targeting Rules */}
          <div className="border-t border-slate-200 pt-5 space-y-4 bg-slate-50 p-4 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Audience Targeting & Reach
                </h3>
                <p className="text-[11px] text-slate-500">Filter which employees receive this announcement.</p>
              </div>
              <button
                type="button"
                onClick={calculateReach}
                disabled={calculatingReach}
                className="bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-medium px-3 py-1.5 rounded-lg shadow-sm transition"
              >
                {calculatingReach ? "Calculating..." : "Preview Reach"}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Audience Scope</label>
                <select
                  value={audienceType}
                  onChange={(e) => setAudienceType(e.target.value)}
                  className="w-full border border-slate-300 bg-white rounded-lg px-2.5 py-1.5 text-xs text-slate-900 mt-1"
                >
                  <option value="ALL_EMPLOYEES">All Company Employees</option>
                  <option value="DEPARTMENT">Specific Department</option>
                  <option value="LOCATION">Specific Location</option>
                  <option value="MANAGERS_ONLY">People Managers Only</option>
                </select>
              </div>

              {audienceType === "DEPARTMENT" && (
                <div>
                  <label className="text-[11px] font-semibold text-slate-600">Department Name</label>
                  <input
                    type="text"
                    value={targetDepartment}
                    onChange={(e) => setTargetDepartment(e.target.value)}
                    placeholder="e.g. Engineering, Sales"
                    className="w-full border border-slate-300 bg-white rounded-lg px-2.5 py-1.5 text-xs text-slate-900 mt-1"
                  />
                </div>
              )}

              {audienceType === "LOCATION" && (
                <div>
                  <label className="text-[11px] font-semibold text-slate-600">Location Reference</label>
                  <input
                    type="text"
                    value={targetLocation}
                    onChange={(e) => setTargetLocation(e.target.value)}
                    placeholder="e.g. Bangalore, Remote"
                    className="w-full border border-slate-300 bg-white rounded-lg px-2.5 py-1.5 text-xs text-slate-900 mt-1"
                  />
                </div>
              )}

              {reachEstimate !== null && (
                <div className="flex items-center">
                  <span className="text-xs bg-indigo-100 text-indigo-800 font-semibold px-3 py-2 rounded-lg">
                    Estimated Audience: {reachEstimate} employees
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setActiveTab("broadcasts")}
              className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-4 py-2 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-5 py-2 rounded-lg shadow-sm transition"
            >
              {isSubmitting ? "Saving..." : "Create & Schedule Broadcast"}
            </button>
          </div>
        </form>
      )}

      {/* Templates Tab */}
      {activeTab === "templates" && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900">Communication Templates</h2>
            <button
              onClick={() => alert("Template creation dialog")}
              className="bg-slate-900 text-white text-xs font-semibold px-3 py-1.5 rounded-lg"
            >
              + New Template
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {!templates || templates.length === 0 ? (
              <p className="text-xs text-slate-400 col-span-2 text-center py-6">No templates found.</p>
            ) : (
              templates.map((tpl: any) => (
                <div key={tpl.id} className="border border-slate-200 rounded-xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] bg-slate-100 text-slate-700 font-bold px-2 py-0.5 rounded uppercase">
                      {tpl.template_type}
                    </span>
                    <span className="text-[11px] text-slate-400">{tpl.category}</span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{tpl.name}</h3>
                  <p className="text-xs text-slate-600 line-clamp-3 font-mono bg-slate-50 p-2 rounded border border-slate-100">
                    {tpl.body_template}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Search Analytics Tab */}
      {activeTab === "analytics" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Searches</p>
              <p className="text-2xl font-extrabold text-slate-900 mt-2">
                {searchAnalytics?.total_searches || 0}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">Queries logged across portal</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Zero-Result Searches</p>
              <p className="text-2xl font-extrabold text-amber-600 mt-2">
                {searchAnalytics?.zero_results_count || 0}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">Knowledge gaps to address</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Privacy Standard</p>
              <p className="text-base font-bold text-emerald-600 mt-2">SHA-256 Hashed</p>
              <p className="text-[11px] text-slate-400 mt-1">No employee identity linked</p>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Search Governance & Query Audit Logs</h3>
            <p className="text-xs text-slate-500">
              Zero-result search telemetry is pseudonymized to preserve employee privacy while alerting knowledge administrators to missing articles.
            </p>

            <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 text-xs">
              <div className="bg-slate-50 px-4 py-2 font-semibold text-slate-600 grid grid-cols-3">
                <span>Query Hash (SHA-256)</span>
                <span className="text-center">Results Returned</span>
                <span className="text-right">Timestamp</span>
              </div>
              {!searchAnalytics?.recent_searches || searchAnalytics.recent_searches.length === 0 ? (
                <div className="p-4 text-center text-slate-400">No search logs recorded.</div>
              ) : (
                searchAnalytics.recent_searches.map((log: any) => (
                  <div key={log.id} className="px-4 py-2.5 grid grid-cols-3 items-center">
                    <span className="font-mono text-[11px] text-slate-600 truncate">{log.query_hash}</span>
                    <span className="text-center font-semibold">{log.results_count}</span>
                    <span className="text-right text-slate-400">
                      {new Date(log.created_at).toLocaleString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
