"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function CommunicationsCenterPage() {
  const [activeTab, setActiveTab] = useState<"feed" | "preferences">("feed");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<any | null>(null);
  const [acknowledgementNotes, setAcknowledgementNotes] = useState("");
  const [submittingAck, setSubmittingAck] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Queries
  const { data: announcements, mutate: mutateAnnouncements } = useSWR(
    `/api/v3/communications/announcements${unreadOnly ? "?unread_only=true" : ""}`,
    fetcher
  );
  const { data: criticalAnnouncements } = useSWR(
    "/api/v3/communications/announcements/critical",
    fetcher
  );
  const { data: preferences, mutate: mutatePreferences } = useSWR(
    "/api/v3/communications/preferences",
    fetcher
  );

  const handleOpenAnnouncement = async (ann: any) => {
    setSelectedAnnouncement(ann);
    setAcknowledgementNotes("");
    try {
      // Record read receipt idempotently
      await api.post(`/api/v3/communications/announcements/${ann.id}/read`);
      mutateAnnouncements();
    } catch {
      // Ignored if already read
    }
  };

  const handleAcknowledge = async () => {
    if (!selectedAnnouncement) return;
    setSubmittingAck(true);
    try {
      await api.post(`/api/v3/communications/announcements/${selectedAnnouncement.id}/acknowledge`, {
        notes: acknowledgementNotes || "Acknowledged via Communications Center",
      });
      setStatusMessage("Acknowledgement submitted successfully!");
      setSelectedAnnouncement((prev: any) => ({ ...prev, is_acknowledged_by_me: true }));
      mutateAnnouncements();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Acknowledgement failed");
    } finally {
      setSubmittingAck(false);
    }
  };

  const handleUpdatePref = async (
    category: string,
    email: boolean,
    inApp: boolean,
    sms: boolean
  ) => {
    try {
      await api.put(`/api/v3/communications/preferences/${category}`, {
        email_enabled: email,
        in_app_enabled: inApp,
        sms_enabled: sms,
      });
      mutatePreferences();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to update preference");
    }
  };

  const criticalBannerItem = criticalAnnouncements && criticalAnnouncements.length > 0
    ? criticalAnnouncements[0]
    : null;

  return (
    <div className="space-y-6">
      {/* Top CRITICAL Banner if active */}
      {criticalBannerItem && (
        <div className="bg-rose-600 text-white rounded-xl p-4 shadow-lg flex items-start justify-between gap-4 border border-rose-500 animate-pulse">
          <div className="flex items-start gap-3">
            <span className="text-2xl">🚨</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] bg-rose-900 text-rose-100 font-extrabold px-2 py-0.5 rounded uppercase tracking-wider">
                  URGENT NOTICE
                </span>
                <span className="text-xs text-rose-200">
                  {new Date(criticalBannerItem.publish_at).toLocaleDateString()}
                </span>
              </div>
              <h2 className="text-base font-bold mt-1">{criticalBannerItem.title}</h2>
              <p className="text-xs text-rose-100 mt-1 max-w-2xl line-clamp-2">
                {criticalBannerItem.summary || criticalBannerItem.content_reference}
              </p>
            </div>
          </div>
          <button
            onClick={() => handleOpenAnnouncement(criticalBannerItem)}
            className="shrink-0 bg-white text-rose-700 hover:bg-rose-50 font-bold text-xs px-3.5 py-2 rounded-lg shadow-sm transition"
          >
            Review & Acknowledge
          </button>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📢</span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Communications Center</h1>
          </div>
          <p className="text-slate-500 text-xs mt-1">
            Company broadcasts, departmental announcements, and policy change notices.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab("feed")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
              activeTab === "feed"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Broadcast Feed
          </button>
          <button
            onClick={() => setActiveTab("preferences")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
              activeTab === "preferences"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Delivery Preferences
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs p-3 rounded-lg flex items-center justify-between">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="font-bold text-slate-500">×</button>
        </div>
      )}

      {activeTab === "feed" && (
        <div className="space-y-4">
          {/* Feed Filter Toolbar */}
          <div className="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-500">Filter:</span>
              <button
                onClick={() => setUnreadOnly(false)}
                className={`text-xs px-2.5 py-1 rounded font-medium transition ${
                  !unreadOnly ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                All Announcements
              </button>
              <button
                onClick={() => setUnreadOnly(true)}
                className={`text-xs px-2.5 py-1 rounded font-medium transition ${
                  unreadOnly ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Unread Only
              </button>
            </div>
            <span className="text-xs text-slate-400">
              {announcements ? `${announcements.length} broadcasts` : "Loading..."}
            </span>
          </div>

          {/* Announcements List */}
          <div className="space-y-3">
            {!announcements || announcements.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
                <p className="text-3xl mb-2">📬</p>
                <p className="font-semibold text-slate-800">No announcements to display</p>
                <p className="text-xs text-slate-400 mt-1">You are all caught up with company news!</p>
              </div>
            ) : (
              announcements.map((ann: any) => {
                const isCritical = ann.priority === "CRITICAL";
                const isHigh = ann.priority === "HIGH";

                return (
                  <div
                    key={ann.id}
                    onClick={() => handleOpenAnnouncement(ann)}
                    className={`bg-white border rounded-xl p-5 shadow-sm hover:shadow-md transition cursor-pointer ${
                      isCritical
                        ? "border-rose-300 bg-rose-50/20"
                        : isHigh
                        ? "border-amber-200 bg-amber-50/10"
                        : "border-slate-200"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                              isCritical
                                ? "bg-rose-100 text-rose-700 border border-rose-300"
                                : isHigh
                                ? "bg-amber-100 text-amber-800 border border-amber-300"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {ann.priority}
                          </span>
                          <span className="text-[10px] bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded uppercase tracking-wider">
                            {ann.announcement_type.replace("_", " ")}
                          </span>
                          {ann.acknowledgement_required && (
                            <span className="text-[10px] bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded">
                              Acknowledgement Required
                            </span>
                          )}
                          {!ann.is_read_by_me && (
                            <span className="w-2 h-2 rounded-full bg-blue-600 inline-block" title="Unread" />
                          )}
                        </div>

                        <h3 className="text-base font-bold text-slate-900 hover:text-indigo-600 transition">
                          {ann.title}
                        </h3>

                        {ann.summary && (
                          <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                            {ann.summary}
                          </p>
                        )}
                      </div>

                      <div className="text-right shrink-0">
                        <span className="text-xs text-slate-400">
                          {new Date(ann.publish_at).toLocaleDateString()}
                        </span>
                        <div className="mt-2">
                          {ann.is_acknowledged_by_me ? (
                            <span className="text-[11px] bg-emerald-100 text-emerald-800 font-medium px-2 py-0.5 rounded">
                              ✓ Acknowledged
                            </span>
                          ) : ann.acknowledgement_required ? (
                            <span className="text-[11px] bg-amber-100 text-amber-800 font-medium px-2 py-0.5 rounded">
                              Pending Ack
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {activeTab === "preferences" && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">Communication & Notification Preferences</h2>
            <p className="text-xs text-slate-500 mt-1">
              Choose how you receive notifications across various communication channels. Critical HR and compliance alerts cannot be disabled.
            </p>
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
            <div className="bg-slate-50 px-4 py-3 grid grid-cols-4 text-xs font-semibold text-slate-600">
              <span className="col-span-1">Category</span>
              <span className="text-center">Email</span>
              <span className="text-center">In-App Banner</span>
              <span className="text-center">SMS Alerts</span>
            </div>

            {[
              { cat: "HR_UPDATES", label: "Mandatory HR & Policy Notices", mandatory: true },
              { cat: "SAFETY", label: "Workplace Safety & Critical Alerts", mandatory: true },
              { cat: "COMPANY_NEWS", label: "Company News & Town Halls", mandatory: false },
              { cat: "BENEFITS", label: "Benefits & Open Enrollment", mandatory: false },
              { cat: "IT_ALERTS", label: "IT Maintenance & Security Bulletins", mandatory: false },
              { cat: "RECOGNITION", label: "Culture, Awards & Celebrations", mandatory: false },
            ].map((item) => {
              const pref = (preferences || []).find((p: any) => p.category === item.cat) || {
                email_enabled: true,
                in_app_enabled: true,
                sms_enabled: false,
              };

              return (
                <div key={item.cat} className="px-4 py-3.5 grid grid-cols-4 items-center text-xs">
                  <div className="col-span-1">
                    <p className="font-semibold text-slate-900">{item.label}</p>
                    {item.mandatory && (
                      <span className="text-[10px] text-amber-700 font-medium">
                        * In-app alerts mandatory for compliance
                      </span>
                    )}
                  </div>

                  <div className="text-center">
                    <input
                      type="checkbox"
                      checked={pref.email_enabled}
                      onChange={(e) =>
                        handleUpdatePref(item.cat, e.target.checked, pref.in_app_enabled, pref.sms_enabled)
                      }
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </div>

                  <div className="text-center">
                    <input
                      type="checkbox"
                      checked={pref.in_app_enabled}
                      disabled={item.mandatory}
                      onChange={(e) =>
                        handleUpdatePref(item.cat, pref.email_enabled, e.target.checked, pref.sms_enabled)
                      }
                      className={`rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 ${
                        item.mandatory ? "opacity-50 cursor-not-allowed" : ""
                      }`}
                    />
                  </div>

                  <div className="text-center">
                    <input
                      type="checkbox"
                      checked={pref.sms_enabled}
                      onChange={(e) =>
                        handleUpdatePref(item.cat, pref.email_enabled, pref.in_app_enabled, e.target.checked)
                      }
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Announcement Detail Modal */}
      {selectedAnnouncement && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-6 space-y-6">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded uppercase">
                    {selectedAnnouncement.priority}
                  </span>
                  <span className="text-[10px] bg-slate-100 text-slate-700 font-semibold px-2 py-0.5 rounded uppercase">
                    {selectedAnnouncement.announcement_type}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-900">{selectedAnnouncement.title}</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Published {new Date(selectedAnnouncement.publish_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => setSelectedAnnouncement(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="prose prose-slate max-w-none text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">
              {selectedAnnouncement.content_reference || selectedAnnouncement.summary}
            </div>

            {/* Acknowledgement Box */}
            {selectedAnnouncement.acknowledgement_required && (
              <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">✍️</span>
                  <h3 className="text-sm font-bold text-purple-900">Acknowledgement Required</h3>
                </div>
                <p className="text-xs text-purple-700">
                  Please review the above announcement thoroughly. By clicking acknowledge, you confirm that you have read and understood its contents.
                </p>

                {selectedAnnouncement.is_acknowledged_by_me ? (
                  <div className="bg-emerald-100 text-emerald-800 font-semibold text-xs p-3 rounded-lg flex items-center gap-2">
                    <span>✓</span>
                    <span>You have acknowledged this announcement.</span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={acknowledgementNotes}
                      onChange={(e) => setAcknowledgementNotes(e.target.value)}
                      placeholder="Optional notes or confirmation remarks..."
                      className="w-full bg-white border border-purple-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      onClick={handleAcknowledge}
                      disabled={submittingAck}
                      className="w-full bg-purple-700 hover:bg-purple-800 text-white font-bold text-xs py-2.5 rounded-lg shadow-sm transition"
                    >
                      {submittingAck ? "Submitting..." : "Confirm & Acknowledge Announcement"}
                    </button>
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedAnnouncement(null)}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-4 py-2 rounded-lg transition"
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
