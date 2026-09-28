"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export type EngagementTab =
  | "overview"
  | "surveys"
  | "campaigns"
  | "questions"
  | "analytics"
  | "action-plans"
  | "recognition"
  | "culture"
  | "team"
  | "my-experience";

interface EngagementWorkspaceProps {
  initialTab?: EngagementTab;
}

export default function EngagementWorkspace({ initialTab = "overview" }: EngagementWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<EngagementTab>(initialTab);

  // Data endpoints
  const { data: hrDashboard, mutate: mutateHrDashboard } = useSWR("/api/v3/engagement/dashboard", fetcher);
  const { data: teamDashboard, mutate: mutateTeamDashboard } = useSWR("/api/v3/engagement/team-dashboard", fetcher);
  const { data: myExperience, mutate: mutateMyExperience } = useSWR("/api/v3/engagement/my-experience", fetcher);
  const { data: templates, mutate: mutateTemplates } = useSWR("/api/v3/engagement/templates", fetcher);
  const { data: campaigns, mutate: mutateCampaigns } = useSWR("/api/v3/engagement/campaigns", fetcher);
  const { data: questions } = useSWR("/api/v3/engagement/questions", fetcher);
  const { data: actionPlans, mutate: mutateActionPlans } = useSWR("/api/v3/engagement/action-plans", fetcher);
  const { data: recognitionPrograms } = useSWR("/api/v3/engagement/recognition/programs", fetcher);
  const { data: recognitionAwards, mutate: mutateRecognitionAwards } = useSWR("/api/v3/engagement/recognition/awards", fetcher);
  const { data: awardDefinitions } = useSWR("/api/v3/engagement/awards", fetcher);
  const { data: awardNominations, mutate: mutateAwardNominations } = useSWR("/api/v3/engagement/awards/nominations", fetcher);
  const { data: cultureInitiatives, mutate: mutateCulture } = useSWR("/api/v3/engagement/culture/initiatives", fetcher);
  const { data: suggestions, mutate: mutateSuggestions } = useSWR("/api/v3/engagement/suggestions", fetcher);

  // Selected Campaign for Analytics
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const { data: campaignAnalytics } = useSWR(
    selectedCampaignId ? `/api/v3/engagement/campaigns/${selectedCampaignId}/results` : null,
    fetcher
  );

  // Form states
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Give recognition state
  const [recProgramId, setRecProgramId] = useState("");
  const [recRecipientId, setRecRecipientId] = useState("");
  const [recTitle, setRecTitle] = useState("");
  const [recMessage, setRecMessage] = useState("");
  const [submittingRec, setSubmittingRec] = useState(false);

  // New suggestion state
  const [suggCategory, setSuggCategory] = useState("WELLBEING");
  const [suggTitle, setSuggTitle] = useState("");
  const [suggDesc, setSuggDesc] = useState("");
  const [suggAnon, setSuggAnon] = useState(true);
  const [submittingSugg, setSubmittingSugg] = useState(false);

  // Handlers
  const handlePublishCampaign = async (id: string) => {
    try {
      await api.post(`/api/v3/engagement/campaigns/${id}/publish`);
      setStatusMessage("Campaign activated and invitations dispatched!");
      mutateCampaigns();
      mutateHrDashboard();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Failed to publish campaign");
    }
  };

  const handleCloseCampaign = async (id: string) => {
    try {
      await api.post(`/api/v3/engagement/campaigns/${id}/close`);
      setStatusMessage("Campaign closed successfully.");
      mutateCampaigns();
      mutateHrDashboard();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Failed to close campaign");
    }
  };

  const handleGiveRecognition = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingRec(true);
    setErrorMessage(null);
    try {
      await api.post("/api/v3/engagement/recognition/awards", {
        program_id: recProgramId || (recognitionPrograms?.[0]?.id ?? ""),
        recipient_person_id: recRecipientId,
        title: recTitle,
        message: recMessage,
        category: "VALUES",
        visibility: "PUBLIC",
      });
      setStatusMessage("Recognition awarded successfully!");
      setRecTitle("");
      setRecMessage("");
      mutateRecognitionAwards();
      mutateMyExperience();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Failed to submit recognition");
    } finally {
      setSubmittingRec(false);
    }
  };

  const handleSubmitSuggestion = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingSugg(true);
    setErrorMessage(null);
    try {
      await api.post("/api/v3/engagement/suggestions", {
        category: suggCategory,
        title: suggTitle,
        description: suggDesc,
        anonymous: suggAnon,
      });
      setStatusMessage("Suggestion submitted to leadership!");
      setSuggTitle("");
      setSuggDesc("");
      mutateSuggestions();
      mutateMyExperience();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Failed to submit suggestion");
    } finally {
      setSubmittingSugg(false);
    }
  };

  const handleVoteSuggestion = async (id: string) => {
    try {
      await api.post(`/api/v3/engagement/suggestions/${id}/vote`);
      mutateSuggestions();
      mutateMyExperience();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Failed to vote");
    }
  };

  const handleJoinInitiative = async (id: string) => {
    try {
      await api.post(`/api/v3/engagement/culture/initiatives/${id}/participation`, {
        initiative_id: id,
        participation_type: "PARTICIPANT",
      });
      setStatusMessage("Joined culture initiative successfully!");
      mutateCulture();
      mutateMyExperience();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || "Already joined or failed to join");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            Employee Engagement & Culture Platform
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Enterprise surveys, anonymity-preserved feedback, peer recognition, and organizational culture initiatives.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            Privacy Invariant: 5+ Min Anonymity Threshold
          </span>
        </div>
      </div>

      {/* Notifications */}
      {statusMessage && (
        <div className="p-4 rounded-md bg-emerald-50 border border-emerald-200 flex justify-between items-center text-emerald-800 text-sm">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="text-emerald-600 hover:text-emerald-900 font-bold">×</button>
        </div>
      )}
      {errorMessage && (
        <div className="p-4 rounded-md bg-rose-50 border border-rose-200 flex justify-between items-center text-rose-800 text-sm">
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="text-rose-600 hover:text-rose-900 font-bold">×</button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 overflow-x-auto">
        <nav className="-mb-px flex space-x-6 min-w-max">
          {[
            { id: "overview", label: "HR Overview" },
            { id: "surveys", label: "Survey Templates" },
            { id: "campaigns", label: "Campaigns" },
            { id: "questions", label: "Question Bank" },
            { id: "analytics", label: "Analytics & eNPS" },
            { id: "action-plans", label: "Action Plans" },
            { id: "recognition", label: "Recognition & Awards" },
            { id: "culture", label: "Culture Initiatives" },
            { id: "team", label: "Manager Team View" },
            { id: "my-experience", label: "My Experience" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as EngagementTab)}
              className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* 1. Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <div className="bg-white overflow-hidden shadow rounded-lg p-5 border border-gray-100">
              <dt className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Campaigns</dt>
              <dd className="mt-2 text-3xl font-extrabold text-indigo-600">
                {hrDashboard?.active_campaigns_count ?? 0}
              </dd>
              <p className="text-xs text-gray-500 mt-1">Live survey distributions</p>
            </div>
            <div className="bg-white overflow-hidden shadow rounded-lg p-5 border border-gray-100">
              <dt className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Avg. Participation</dt>
              <dd className="mt-2 text-3xl font-extrabold text-emerald-600">
                {hrDashboard?.average_participation_rate ?? 0}%
              </dd>
              <p className="text-xs text-gray-500 mt-1">Across all eligible cohorts</p>
            </div>
            <div className="bg-white overflow-hidden shadow rounded-lg p-5 border border-gray-100">
              <dt className="text-xs font-semibold text-gray-500 uppercase tracking-wider">eNPS Score</dt>
              <dd className="mt-2 text-3xl font-extrabold text-blue-600">
                {hrDashboard?.average_enps != null ? `+${hrDashboard.average_enps}` : "N/A"}
              </dd>
              <p className="text-xs text-gray-500 mt-1">Employee Net Promoter benchmark</p>
            </div>
            <div className="bg-white overflow-hidden shadow rounded-lg p-5 border border-gray-100">
              <dt className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Recognitions Awarded</dt>
              <dd className="mt-2 text-3xl font-extrabold text-amber-600">
                {hrDashboard?.total_recognitions_awarded ?? 0}
              </dd>
              <p className="text-xs text-gray-500 mt-1">Peer & manager kudos granted</p>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg border border-gray-200 p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Active & Recent Survey Campaigns</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Campaign Name</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Audience</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Anonymity</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Responses</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {(campaigns || []).map((c: any) => (
                    <tr key={c.id}>
                      <td className="px-4 py-3 font-medium text-gray-900">{c.name}</td>
                      <td className="px-4 py-3 text-gray-600">{c.audience_type}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${c.anonymous ? "bg-purple-100 text-purple-800" : "bg-gray-100 text-gray-800"}`}>
                          {c.anonymous ? "Anonymous (Safe)" : "Identified"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${c.status === "ACTIVE" ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-800"}`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{c.response_count} received</td>
                      <td className="px-4 py-3 text-right space-x-2">
                        {c.status === "DRAFT" && (
                          <button
                            onClick={() => handlePublishCampaign(c.id)}
                            className="text-xs bg-indigo-600 text-white px-2.5 py-1 rounded hover:bg-indigo-700"
                          >
                            Publish
                          </button>
                        )}
                        {c.status === "ACTIVE" && (
                          <button
                            onClick={() => handleCloseCampaign(c.id)}
                            className="text-xs bg-gray-600 text-white px-2.5 py-1 rounded hover:bg-gray-700"
                          >
                            Close
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setSelectedCampaignId(c.id);
                            setActiveTab("analytics");
                          }}
                          className="text-xs text-indigo-600 hover:text-indigo-900 font-medium"
                        >
                          View Analytics →
                        </button>
                      </td>
                    </tr>
                  ))}
                  {(!campaigns || campaigns.length === 0) && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        No campaigns found. Create one from the Campaigns tab.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. Survey Templates Tab */}
      {activeTab === "surveys" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Survey Templates Catalog</h2>
              <p className="text-sm text-gray-500">Standardized question batteries for pulse, onboarding, exit, and engagement.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {(templates || []).map((t: any) => (
              <div key={t.id} className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-3">
                <div className="flex justify-between items-start">
                  <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700">
                    {t.survey_type}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">~{t.estimated_minutes} mins</span>
                </div>
                <h3 className="font-bold text-gray-900 text-base">{t.name}</h3>
                <p className="text-xs text-gray-600 line-clamp-2">{t.description || "No description provided."}</p>
                <div className="pt-2 border-t border-gray-100 flex justify-between items-center text-xs text-gray-500">
                  <span>{t.questions?.length ?? 0} Questions</span>
                  <span className="font-semibold text-emerald-600">{t.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Campaigns Tab */}
      {activeTab === "campaigns" && (
        <div className="bg-white shadow rounded-lg border border-gray-200 p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">Survey Campaigns</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Campaign</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Audience</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Timeline</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Anonymity Threshold</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {(campaigns || []).map((c: any) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{c.name}</div>
                      <div className="text-xs text-gray-500">{c.template_name || "Template"}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{c.audience_type}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(c.start_at).toLocaleDateString()} - {new Date(c.end_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
                        Min {c.minimum_anonymity_threshold} Responses
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${c.status === "ACTIVE" ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-800"}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      {c.status === "DRAFT" && (
                        <button
                          onClick={() => handlePublishCampaign(c.id)}
                          className="text-xs bg-indigo-600 text-white px-2.5 py-1 rounded hover:bg-indigo-700"
                        >
                          Publish
                        </button>
                      )}
                      {c.status === "ACTIVE" && (
                        <button
                          onClick={() => handleCloseCampaign(c.id)}
                          className="text-xs bg-gray-600 text-white px-2.5 py-1 rounded hover:bg-gray-700"
                        >
                          Close
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. Question Bank Tab */}
      {activeTab === "questions" && (
        <div className="bg-white shadow rounded-lg border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Survey Question Bank</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(questions || []).map((q: any) => (
              <div key={q.id} className="p-4 rounded-lg border border-gray-200 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">{q.category}</span>
                  <span className="text-xs text-gray-500 font-mono">{q.question_type}</span>
                </div>
                <p className="text-sm font-medium text-gray-900">{q.question_text}</p>
                <div className="flex gap-2 text-xs text-gray-400">
                  <span>Scale: {q.scale_min ?? 1} - {q.scale_max ?? 5}</span>
                  <span>•</span>
                  <span>{q.required ? "Required" : "Optional"}</span>
                  <span>•</span>
                  <span>{q.anonymous ? "Anonymous Answer" : "Named"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Analytics & eNPS Tab */}
      {activeTab === "analytics" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-lg border border-gray-200">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Engagement & Survey Analytics</h2>
              <p className="text-xs text-gray-500">Aggregated results protected by configurable anonymity thresholds.</p>
            </div>
            <select
              value={selectedCampaignId || ""}
              onChange={(e) => setSelectedCampaignId(e.target.value)}
              className="border border-gray-300 rounded-md text-sm p-2 bg-white"
            >
              <option value="">Select a Campaign...</option>
              {(campaigns || []).map((c: any) => (
                <option key={c.id} value={c.id}>{c.name} ({c.status})</option>
              ))}
            </select>
          </div>

          {campaignAnalytics ? (
            <div className="space-y-6">
              {!campaignAnalytics.is_threshold_met ? (
                <div className="p-5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900">
                  <h4 className="font-bold text-sm">Privacy Protection Active: Anonymity Threshold Not Met</h4>
                  <p className="text-xs mt-1">{campaignAnalytics.threshold_notice}</p>
                  <p className="text-xs mt-2 font-mono text-amber-700">
                    Sample size: {campaignAnalytics.sample_size} | Minimum required: {campaignAnalytics.minimum_anonymity_threshold}
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                    <div className="bg-white p-5 rounded-lg border border-gray-200">
                      <dt className="text-xs text-gray-500 uppercase font-semibold">Overall Engagement Score</dt>
                      <dd className="text-3xl font-extrabold text-indigo-600 mt-2">
                        {campaignAnalytics.overall_engagement_score} / 5.0
                      </dd>
                      <p className="text-xs text-gray-400 mt-1">SURVEY RESULT • AGGREGATED</p>
                    </div>
                    <div className="bg-white p-5 rounded-lg border border-gray-200">
                      <dt className="text-xs text-gray-500 uppercase font-semibold">eNPS Score</dt>
                      <dd className="text-3xl font-extrabold text-emerald-600 mt-2">
                        {campaignAnalytics.enps_score != null ? `+${campaignAnalytics.enps_score}` : "N/A"}
                      </dd>
                      <p className="text-xs text-gray-400 mt-1">% Promoters minus % Detractors</p>
                    </div>
                    <div className="bg-white p-5 rounded-lg border border-gray-200">
                      <dt className="text-xs text-gray-500 uppercase font-semibold">Valid Sample Size</dt>
                      <dd className="text-3xl font-extrabold text-gray-900 mt-2">
                        {campaignAnalytics.sample_size}
                      </dd>
                      <p className="text-xs text-emerald-600 mt-1 font-semibold">Threshold met (Min: {campaignAnalytics.minimum_anonymity_threshold})</p>
                    </div>
                  </div>

                  {/* Category Scores */}
                  <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4">
                    <h3 className="font-bold text-gray-900 text-sm">Category Score Breakdown</h3>
                    <div className="space-y-3">
                      {(campaignAnalytics.category_scores || []).map((cat: any) => (
                        <div key={cat.category} className="space-y-1">
                          <div className="flex justify-between text-xs font-semibold">
                            <span>{cat.category}</span>
                            <span>{cat.average_score} / 5.0 ({cat.favorable_percent}% favorable)</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-indigo-600 h-2 rounded-full"
                              style={{ width: `${Math.min(100, (cat.average_score / 5) * 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="text-center py-12 bg-white rounded-lg border border-gray-200 text-gray-500 text-sm">
              Please select a campaign from the dropdown above to view aggregated results.
            </div>
          )}
        </div>
      )}

      {/* 6. Action Plans Tab */}
      {activeTab === "action-plans" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">Survey Follow-Up Action Plans</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {(actionPlans || []).map((p: any) => (
              <div key={p.id} className="bg-white rounded-lg border border-gray-200 p-5 space-y-3">
                <div className="flex justify-between items-start">
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${p.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                    {p.status}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">Due: {p.due_date || "Open"}</span>
                </div>
                <h3 className="font-bold text-gray-900">{p.title}</h3>
                <p className="text-xs text-gray-600">{p.description || "No description."}</p>
                <div className="pt-2 border-t border-gray-100 space-y-2">
                  <h4 className="text-xs font-bold text-gray-700">Action Items ({p.items?.length ?? 0}):</h4>
                  {(p.items || []).map((item: any) => (
                    <div key={item.id} className="flex items-center justify-between text-xs bg-gray-50 p-2 rounded">
                      <span className={item.status === "COMPLETED" ? "line-through text-gray-400" : "text-gray-800"}>
                        {item.action}
                      </span>
                      <span className="font-semibold text-gray-500">{item.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 7. Recognition & Awards Tab */}
      {activeTab === "recognition" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recognition Wall */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Peer Recognition & Kudos Wall</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {(recognitionAwards || []).map((a: any) => (
                <div key={a.id} className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm space-y-3">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-indigo-600">{a.category}</span>
                    <span className="text-gray-400">{new Date(a.awarded_at).toLocaleDateString()}</span>
                  </div>
                  <h3 className="font-bold text-gray-900 text-sm">{a.title}</h3>
                  <p className="text-xs text-gray-600 italic">"{a.message}"</p>
                  <div className="pt-2 border-t border-gray-100 flex justify-between text-xs text-gray-500">
                    <span>From: <strong>{a.giver_name || "Colleague"}</strong></span>
                    <span>To: <strong>{a.recipient_name || "Team Member"}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Give Recognition Form */}
          <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm space-y-4 h-fit">
            <h3 className="font-bold text-gray-900 text-base">Give Peer Kudos</h3>
            <form onSubmit={handleGiveRecognition} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Recipient Person ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. person-id"
                  value={recRecipientId}
                  onChange={(e) => setRecRecipientId(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Great Collaboration on Sprint"
                  value={recTitle}
                  onChange={(e) => setRecTitle(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Kudos Message</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Describe how their contribution made a difference..."
                  value={recMessage}
                  onChange={(e) => setRecMessage(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-xs"
                />
              </div>
              <button
                type="submit"
                disabled={submittingRec}
                className="w-full bg-indigo-600 text-white font-medium py-2 rounded text-xs hover:bg-indigo-700 disabled:opacity-50"
              >
                {submittingRec ? "Awarding..." : "Send Recognition"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* 8. Culture Initiatives Tab */}
      {activeTab === "culture" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">Organizational Culture & Wellbeing Initiatives</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {(cultureInitiatives || []).map((ci: any) => (
              <div key={ci.id} className="bg-white rounded-lg border border-gray-200 p-5 space-y-3 shadow-sm flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                      {ci.category}
                    </span>
                    <span className="text-xs text-emerald-600 font-semibold">{ci.status}</span>
                  </div>
                  <h3 className="font-bold text-gray-900">{ci.name}</h3>
                  <p className="text-xs text-gray-600">{ci.description || "Community program."}</p>
                </div>
                <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-xs text-gray-500 font-medium">
                    {ci.participant_count ?? 0} {ci.target_participants ? `/ ${ci.target_participants}` : ""} joined
                  </span>
                  <button
                    onClick={() => handleJoinInitiative(ci.id)}
                    className="text-xs bg-indigo-50 text-indigo-700 font-semibold px-3 py-1 rounded hover:bg-indigo-100"
                  >
                    Join Initiative
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 9. Manager Team Dashboard Tab */}
      {activeTab === "team" && (
        <div className="space-y-6">
          <div className="bg-white p-5 rounded-lg border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Manager Team Engagement Dashboard</h2>
            <p className="text-xs text-gray-500 mt-1">
              Direct team metrics restricted to reporting line. Anonymity threshold strictly enforced.
            </p>
          </div>

          {teamDashboard && (
            <>
              {!teamDashboard.is_threshold_met ? (
                <div className="p-5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900">
                  <h4 className="font-bold text-sm">Privacy Invariant Active: Anonymity Threshold</h4>
                  <p className="text-xs mt-1">{teamDashboard.threshold_notice}</p>
                  <p className="text-xs mt-2 font-mono text-amber-700">
                    Team Size: {teamDashboard.team_size} | Minimum required for aggregate breakdown: {teamDashboard.minimum_anonymity_threshold}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div className="bg-white p-5 rounded-lg border border-gray-200">
                    <dt className="text-xs text-gray-500 uppercase font-semibold">Team Engagement Index</dt>
                    <dd className="text-3xl font-extrabold text-indigo-600 mt-2">
                      {teamDashboard.team_engagement_score} / 5.0
                    </dd>
                    <p className="text-xs text-gray-400 mt-1">AGGREGATED RESULT • SAMPLE SIZE {teamDashboard.team_size}</p>
                  </div>
                  <div className="bg-white p-5 rounded-lg border border-gray-200">
                    <dt className="text-xs text-gray-500 uppercase font-semibold">Team Participation Rate</dt>
                    <dd className="text-3xl font-extrabold text-emerald-600 mt-2">
                      {teamDashboard.team_participation_rate ?? 0}%
                    </dd>
                    <p className="text-xs text-gray-400 mt-1">Completed surveys among direct reports</p>
                  </div>
                </div>
              )}

              {/* Recent team recognition */}
              <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4">
                <h3 className="font-bold text-gray-900 text-sm">Recent Team Kudos & Recognition</h3>
                <div className="space-y-3">
                  {(teamDashboard.recent_team_recognition || []).map((a: any) => (
                    <div key={a.id} className="p-3 bg-gray-50 rounded border border-gray-100 flex justify-between items-center text-xs">
                      <div>
                        <span className="font-bold text-gray-900">{a.title}</span>
                        <p className="text-gray-500 italic mt-0.5">"{a.message}"</p>
                      </div>
                      <span className="font-semibold text-indigo-600">{a.category}</span>
                    </div>
                  ))}
                  {(!teamDashboard.recent_team_recognition || teamDashboard.recent_team_recognition.length === 0) && (
                    <p className="text-xs text-gray-500">No recognition recorded for team members yet.</p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* 10. My Experience Tab */}
      {activeTab === "my-experience" && (
        <div className="space-y-6">
          <div className="bg-white p-5 rounded-lg border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">My Employee Experience Hub</h2>
            <p className="text-xs text-gray-500 mt-1">Your available surveys, recognition activity, and ideas box.</p>
          </div>

          {/* Available Surveys */}
          <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4">
            <h3 className="font-bold text-gray-900 text-sm">Available Surveys Waiting for Response</h3>
            <div className="space-y-3">
              {(myExperience?.available_surveys || []).map((s: any) => (
                <div key={s.campaign_id} className="p-4 bg-indigo-50 border border-indigo-100 rounded-lg flex justify-between items-center">
                  <div>
                    <h4 className="font-bold text-indigo-900 text-sm">{s.campaign_name}</h4>
                    <p className="text-xs text-indigo-700 mt-0.5">{s.description || "Active engagement survey"}</p>
                  </div>
                  <span className="text-xs bg-indigo-600 text-white font-medium px-3 py-1.5 rounded">
                    Open for Feedback
                  </span>
                </div>
              ))}
              {(!myExperience?.available_surveys || myExperience.available_surveys.length === 0) && (
                <p className="text-xs text-gray-500">No pending surveys at this time.</p>
              )}
            </div>
          </div>

          {/* Suggestions Box */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white p-6 rounded-lg border border-gray-200 space-y-4">
              <h3 className="font-bold text-gray-900 text-sm">Employee Suggestions & Ideas Box</h3>
              <div className="space-y-3">
                {(suggestions || []).map((sg: any) => (
                  <div key={sg.id} className="p-4 bg-gray-50 rounded-lg border border-gray-200 flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-indigo-600">{sg.category}</span>
                        <span className="text-xs text-gray-400">•</span>
                        <span className="text-xs text-gray-500">{sg.person_name}</span>
                      </div>
                      <h4 className="font-bold text-gray-900 text-sm">{sg.title}</h4>
                      <p className="text-xs text-gray-600">{sg.description}</p>
                    </div>
                    <button
                      onClick={() => handleVoteSuggestion(sg.id)}
                      className="flex items-center gap-1 text-xs bg-white border border-gray-300 px-2.5 py-1 rounded hover:bg-gray-50 font-semibold"
                    >
                      ▲ {sg.votes_count}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4 h-fit">
              <h3 className="font-bold text-gray-900 text-sm">Submit New Suggestion</h3>
              <form onSubmit={handleSubmitSuggestion} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-gray-700">Category</label>
                  <select
                    value={suggCategory}
                    onChange={(e) => setSuggCategory(e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded p-2"
                  >
                    <option value="WELLBEING">Wellbeing</option>
                    <option value="WORKPLACE">Workplace</option>
                    <option value="PROCESS">Process Improvement</option>
                    <option value="TOOLS">Tools & Infrastructure</option>
                    <option value="CULTURE">Culture & Values</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-gray-700">Title</label>
                  <input
                    type="text"
                    required
                    placeholder="Short idea summary"
                    value={suggTitle}
                    onChange={(e) => setSuggTitle(e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded p-2"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-gray-700">Description</label>
                  <textarea
                    required
                    rows={3}
                    placeholder="Describe how this improves the employee experience..."
                    value={suggDesc}
                    onChange={(e) => setSuggDesc(e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded p-2"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="anon"
                    checked={suggAnon}
                    onChange={(e) => setSuggAnon(e.target.checked)}
                  />
                  <label htmlFor="anon" className="text-gray-700 font-medium">Submit Anonymously</label>
                </div>
                <button
                  type="submit"
                  disabled={submittingSugg}
                  className="w-full bg-indigo-600 text-white font-medium py-2 rounded hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submittingSugg ? "Submitting..." : "Submit Idea"}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
