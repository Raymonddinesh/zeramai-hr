"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function GovernancePage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "inventory" | "retention" | "legal-holds" | "privacy" | "bcp-dr" | "residency"
  >("overview");

  // Data fetching
  const { data: dashboard, mutate: mutateDashboard } = useSWR("/api/v3/governance/dashboard", fetcher);
  const { data: classifications } = useSWR("/api/v3/governance/classifications", fetcher);
  const { data: assets, mutate: mutateAssets } = useSWR("/api/v3/governance/assets", fetcher);
  const { data: retentionPolicies, mutate: mutateRetention } = useSWR("/api/v3/governance/retention-policies", fetcher);
  const { data: lifecycleRecords, mutate: mutateLifecycle } = useSWR("/api/v3/governance/lifecycle/records", fetcher);
  const { data: legalHolds, mutate: mutateHolds } = useSWR("/api/v3/governance/legal-holds", fetcher);
  const { data: privacyRequests, mutate: mutatePrivacy } = useSWR("/api/v3/governance/privacy-requests", fetcher);
  const { data: backupPolicies } = useSWR("/api/v3/governance/backup-policies", fetcher);
  const { data: backupExecutions, mutate: mutateBackups } = useSWR("/api/v3/governance/backup-executions", fetcher);
  const { data: drPolicies } = useSWR("/api/v3/governance/dr-policies", fetcher);
  const { data: drTests, mutate: mutateDRTests } = useSWR("/api/v3/governance/dr-tests", fetcher);
  const { data: bcpPlans, mutate: mutateBCP } = useSWR("/api/v3/governance/bcp", fetcher);
  const { data: residencyPolicies } = useSWR("/api/v3/governance/residency-policies", fetcher);

  // Form states
  const [newHoldName, setNewHoldName] = useState("");
  const [newHoldMatter, setNewHoldMatter] = useState("");
  const [newHoldTargetType, setNewHoldTargetType] = useState("PERSON");
  const [newHoldTargetRef, setNewHoldTargetRef] = useState("");

  const [privacyPersonId, setPrivacyPersonId] = useState("");
  const [privacyType, setPrivacyType] = useState("EXPORT");

  const [evaluatingLifecycle, setEvaluatingLifecycle] = useState(false);
  const [evalResult, setEvalResult] = useState<string | null>(null);

  // Actions
  const handleTriggerLifecycle = async () => {
    setEvaluatingLifecycle(true);
    try {
      const res = await api.post("/api/v3/governance/lifecycle/evaluate", { dry_run: false });
      setEvalResult(`Evaluated ${res.data.total_evaluated} records: ${res.data.eligible_for_archive} archive-eligible, ${res.data.eligible_for_deletion} deletion-eligible, ${res.data.blocked_by_legal_hold} protected by legal hold.`);
      mutateLifecycle();
      mutateDashboard();
    } catch {
      alert("Error executing lifecycle evaluation");
    } finally {
      setEvaluatingLifecycle(false);
    }
  };

  const handleCreateLegalHold = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHoldName || !newHoldMatter) return;
    try {
      await api.post("/api/v3/governance/legal-holds", {
        name: newHoldName,
        matter_reference: newHoldMatter,
        targets: newHoldTargetRef ? [{ target_type: newHoldTargetType, target_reference: newHoldTargetRef }] : [],
      });
      setNewHoldName("");
      setNewHoldMatter("");
      setNewHoldTargetRef("");
      mutateHolds();
      mutateDashboard();
      alert("Legal hold created successfully");
    } catch {
      alert("Failed to issue legal hold");
    }
  };

  const handleReleaseHold = async (holdId: string) => {
    if (!confirm("Are you sure you want to release this legal hold? Governed records will resume standard retention lifecycle.")) return;
    try {
      await api.post(`/api/v3/governance/legal-holds/${holdId}/release`);
      mutateHolds();
      mutateDashboard();
    } catch {
      alert("Failed to release legal hold");
    }
  };

  const handleCreatePrivacyRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/api/v3/governance/privacy-requests", {
        person_id: privacyPersonId || undefined,
        request_type: privacyType,
      });
      setPrivacyPersonId("");
      mutatePrivacy();
      mutateDashboard();
      alert("Privacy request created successfully");
    } catch {
      alert("Failed to create privacy request");
    }
  };

  const handleExportPrivacyData = async (reqId: string) => {
    try {
      const res = await api.post(`/api/v3/governance/privacy-requests/${reqId}/export`);
      const blob = new Blob([JSON.stringify(res.data.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `privacy_export_${res.data.person_id}.json`;
      a.click();
      mutatePrivacy();
    } catch {
      alert("Error generating privacy export");
    }
  };

  const handleAnonymize = async (reqId: string) => {
    if (!confirm("Execute controlled anonymization? Personal PII will be sanitized. Statutory tax & EPF records will be preserved.")) return;
    try {
      const res = await api.post(`/api/v3/governance/privacy-requests/${reqId}/anonymize`);
      if (res.data.blocked_by_legal_hold) {
        alert(`BLOCKED: ${res.data.message}`);
      } else {
        alert(res.data.message);
      }
      mutatePrivacy();
      mutateDashboard();
    } catch {
      alert("Error processing anonymization");
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Governance, Privacy & Business Continuity</h1>
        <p className="text-sm text-gray-500">
          Module 15: Enterprise Data Governance, Statutory Retention, DPDP/GDPR Privacy Rights, Legal Holds & Resilience
        </p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 border-b border-gray-200">
        {[
          { id: "overview", label: "Overview" },
          { id: "inventory", label: "Data Inventory & Classification" },
          { id: "retention", label: "Retention & Lifecycle" },
          { id: "legal-holds", label: "Legal Holds" },
          { id: "privacy", label: "Privacy (DSR / DSAR)" },
          { id: "bcp-dr", label: "BCP & Disaster Recovery" },
          { id: "residency", label: "Data Residency" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
              <div className="text-sm text-gray-500 font-medium">Data Classifications</div>
              <div className="text-2xl font-bold text-gray-900 mt-2">{dashboard?.classifications_count ?? 5}</div>
              <div className="text-xs text-green-600 mt-1">Catalog tiers configured</div>
            </div>
            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
              <div className="text-sm text-gray-500 font-medium">Active Legal Holds</div>
              <div className="text-2xl font-bold text-amber-600 mt-2">{dashboard?.active_legal_holds_count ?? 0}</div>
              <div className="text-xs text-gray-500 mt-1">Enforcing deletion freeze</div>
            </div>
            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
              <div className="text-sm text-gray-500 font-medium">Pending Privacy DSRs</div>
              <div className="text-2xl font-bold text-blue-600 mt-2">{dashboard?.pending_privacy_requests_count ?? 0}</div>
              <div className="text-xs text-gray-500 mt-1">{dashboard?.total_privacy_requests_count ?? 0} total requests</div>
            </div>
            <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
              <div className="text-sm text-gray-500 font-medium">Backup & DR Status</div>
              <div className="text-2xl font-bold text-emerald-600 mt-2">{dashboard?.backup_status ?? "HEALTHY"}</div>
              <div className="text-xs text-gray-500 mt-1">DR Readiness: {dashboard?.dr_readiness_status ?? "READY"}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm space-y-4">
              <h3 className="text-base font-semibold text-gray-900">Governance Compliance Controls</h3>
              <ul className="divide-y divide-gray-100 text-sm">
                <li className="py-2.5 flex justify-between">
                  <span className="text-gray-600">Statutory Tax & Wage Retention</span>
                  <span className="font-medium text-gray-900">7 Years (2555 Days) - IT Act 1961</span>
                </li>
                <li className="py-2.5 flex justify-between">
                  <span className="text-gray-600">DPDP Act 2023 DSR SLA</span>
                  <span className="font-medium text-gray-900">30 Days statutory deadline</span>
                </li>
                <li className="py-2.5 flex justify-between">
                  <span className="text-gray-600">Disaster Recovery RPO / RTO</span>
                  <span className="font-medium text-gray-900">60m RPO / 240m RTO</span>
                </li>
                <li className="py-2.5 flex justify-between">
                  <span className="text-gray-600">Cross-Border Transfer Mandate</span>
                  <span className="font-medium text-red-600">Restricted (India Sovereign)</span>
                </li>
              </ul>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm space-y-4">
              <h3 className="text-base font-semibold text-gray-900">Quick Governance Actions</h3>
              <div className="space-y-3">
                <button
                  onClick={handleTriggerLifecycle}
                  disabled={evaluatingLifecycle}
                  className="w-full text-left p-3 rounded border border-gray-200 hover:bg-gray-50 transition flex justify-between items-center"
                >
                  <div>
                    <div className="font-medium text-gray-900">Evaluate Record Lifecycle</div>
                    <div className="text-xs text-gray-500">Scan retention milestones and flag archive/deletion candidates</div>
                  </div>
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">Run</span>
                </button>

                {evalResult && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800">
                    {evalResult}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DATA INVENTORY */}
      {activeTab === "inventory" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Data Classification Tiers</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 border-b">
                  <tr>
                    <th className="p-3">Code</th>
                    <th className="p-3">Name</th>
                    <th className="p-3">Sensitivity</th>
                    <th className="p-3">Default Retention</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {classifications?.map((c: any) => (
                    <tr key={c.id}>
                      <td className="p-3 font-mono text-xs font-semibold">{c.code}</td>
                      <td className="p-3 font-medium text-gray-900">{c.name}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          c.sensitivity_level === "HIGHLY_RESTRICTED" ? "bg-red-100 text-red-800" :
                          c.sensitivity_level === "RESTRICTED" ? "bg-amber-100 text-amber-800" :
                          c.sensitivity_level === "CONFIDENTIAL" ? "bg-purple-100 text-purple-800" : "bg-gray-100 text-gray-800"
                        }`}>
                          {c.sensitivity_level}
                        </span>
                      </td>
                      <td className="p-3 text-gray-600">{c.default_retention_days ? `${c.default_retention_days} days` : "Indefinite"}</td>
                      <td className="p-3">
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Active</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-semibold text-gray-900">Data Asset Inventory</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 border-b">
                  <tr>
                    <th className="p-3">Asset Name</th>
                    <th className="p-3">Module</th>
                    <th className="p-3">Classification</th>
                    <th className="p-3">Personal Data</th>
                    <th className="p-3">Residency</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {assets && assets.length > 0 ? (
                    assets.map((a: any) => (
                      <tr key={a.id}>
                        <td className="p-3 font-medium text-gray-900">{a.name}</td>
                        <td className="p-3 text-gray-600">{a.source_module}</td>
                        <td className="p-3">{a.classification_name || "Confidential"}</td>
                        <td className="p-3">
                          {a.contains_personal_data ? (
                            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">PII</span>
                          ) : (
                            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">Non-PII</span>
                          )}
                        </td>
                        <td className="p-3 text-gray-600">{a.data_residency}</td>
                        <td className="p-3">
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">{a.status}</span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-4 text-center text-gray-400">No custom data assets cataloged yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: RETENTION & LIFECYCLE */}
      {activeTab === "retention" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Configured Retention Policies</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 border-b">
                  <tr>
                    <th className="p-3">Policy Name</th>
                    <th className="p-3">Record Type</th>
                    <th className="p-3">Retention</th>
                    <th className="p-3">Archive After</th>
                    <th className="p-3">Legal Basis</th>
                    <th className="p-3">Jurisdiction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {retentionPolicies?.map((r: any) => (
                    <tr key={r.id}>
                      <td className="p-3 font-medium text-gray-900">{r.name}</td>
                      <td className="p-3 font-mono text-xs">{r.record_type}</td>
                      <td className="p-3 text-gray-600">{r.retention_period_days} days ({Math.round(r.retention_period_days/365)} yrs)</td>
                      <td className="p-3 text-gray-600">{r.archive_after_days} days</td>
                      <td className="p-3 text-xs text-gray-500 max-w-xs">{r.legal_basis || "Operational Standard"}</td>
                      <td className="p-3 font-semibold text-xs">{r.jurisdiction}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-semibold text-gray-900">Record Lifecycle Evaluation State</h3>
              <button
                onClick={handleTriggerLifecycle}
                disabled={evaluatingLifecycle}
                className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700"
              >
                {evaluatingLifecycle ? "Evaluating..." : "Run Evaluation Now"}
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 border-b">
                  <tr>
                    <th className="p-3">Asset Type</th>
                    <th className="p-3">Asset ID</th>
                    <th className="p-3">Lifecycle Status</th>
                    <th className="p-3">Legal Hold</th>
                    <th className="p-3">Last Evaluated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {lifecycleRecords && lifecycleRecords.length > 0 ? (
                    lifecycleRecords.map((l: any) => (
                      <tr key={l.id}>
                        <td className="p-3 font-medium">{l.asset_type}</td>
                        <td className="p-3 font-mono text-xs text-gray-500">{l.asset_id}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            l.lifecycle_status === "ACTIVE" ? "bg-green-100 text-green-800" :
                            l.lifecycle_status === "ARCHIVED" ? "bg-blue-100 text-blue-800" :
                            l.lifecycle_status === "ANONYMIZED" ? "bg-gray-100 text-gray-700" : "bg-amber-100 text-amber-800"
                          }`}>
                            {l.lifecycle_status}
                          </span>
                        </td>
                        <td className="p-3">
                          {l.legal_hold ? (
                            <span className="text-xs bg-red-100 text-red-800 font-bold px-2 py-0.5 rounded">HELD</span>
                          ) : (
                            <span className="text-xs text-gray-400">No</span>
                          )}
                        </td>
                        <td className="p-3 text-xs text-gray-500">{new Date(l.last_evaluated_at).toLocaleString()}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="p-4 text-center text-gray-400">No lifecycle records indexed. Click 'Run Evaluation Now'.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: LEGAL HOLDS */}
      {activeTab === "legal-holds" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Issue New Legal Hold</h3>
            <form onSubmit={handleCreateLegalHold} className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700">Hold Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Litigation Matter - Dispute A"
                  value={newHoldName}
                  onChange={(e) => setNewHoldName(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Matter Reference / Case #</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. MAT-2026-0042"
                  value={newHoldMatter}
                  onChange={(e) => setNewHoldMatter(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Target Type</label>
                <select
                  value={newHoldTargetType}
                  onChange={(e) => setNewHoldTargetType(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-sm"
                >
                  <option value="PERSON">PERSON</option>
                  <option value="EMPLOYEE">EMPLOYEE</option>
                  <option value="DOCUMENT">DOCUMENT</option>
                  <option value="DEPARTMENT">DEPARTMENT</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Target Reference ID</label>
                <input
                  type="text"
                  placeholder="Person ID or Document ID"
                  value={newHoldTargetRef}
                  onChange={(e) => setNewHoldTargetRef(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-sm"
                />
              </div>
              <div className="md:col-span-4 flex justify-end">
                <button type="submit" className="px-4 py-2 bg-amber-600 text-white rounded text-sm font-medium hover:bg-amber-700">
                  Issue Legal Hold
                </button>
              </div>
            </form>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Active and Historical Legal Holds</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 border-b">
                  <tr>
                    <th className="p-3">Matter Reference</th>
                    <th className="p-3">Title</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Issued Date</th>
                    <th className="p-3">Targets</th>
                    <th className="p-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {legalHolds && legalHolds.length > 0 ? (
                    legalHolds.map((h: any) => (
                      <tr key={h.id}>
                        <td className="p-3 font-mono text-xs font-semibold">{h.matter_reference}</td>
                        <td className="p-3 font-medium text-gray-900">{h.name}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                            h.status === "ACTIVE" ? "bg-red-100 text-red-800" : "bg-gray-100 text-gray-600"
                          }`}>
                            {h.status}
                          </span>
                        </td>
                        <td className="p-3 text-xs text-gray-500">{new Date(h.issued_at).toLocaleDateString()}</td>
                        <td className="p-3 text-xs">
                          {h.targets?.map((t: any) => `${t.target_type}:${t.target_reference}`).join(", ") || "None"}
                        </td>
                        <td className="p-3">
                          {h.status === "ACTIVE" && (
                            <button
                              onClick={() => handleReleaseHold(h.id)}
                              className="text-xs text-red-600 hover:underline font-medium"
                            >
                              Release Hold
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-4 text-center text-gray-400">No legal holds active.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: PRIVACY (DSR / DSAR) */}
      {activeTab === "privacy" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Submit Data Subject Request (DSR / DSAR)</h3>
            <form onSubmit={handleCreatePrivacyRequest} className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700">Target Person ID</label>
                <input
                  type="text"
                  required
                  placeholder="Person ID"
                  value={privacyPersonId}
                  onChange={(e) => setPrivacyPersonId(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Request Type</label>
                <select
                  value={privacyType}
                  onChange={(e) => setPrivacyType(e.target.value)}
                  className="mt-1 w-full border border-gray-300 rounded p-2 text-sm"
                >
                  <option value="EXPORT">EXPORT (Data Portability)</option>
                  <option value="ACCESS">ACCESS (Right to Know)</option>
                  <option value="DELETION">DELETION (Right to be Forgotten)</option>
                  <option value="ANONYMIZATION">ANONYMIZATION (Controlled Erasure)</option>
                  <option value="RECTIFICATION">RECTIFICATION (Data Correction)</option>
                </select>
              </div>
              <div className="flex items-end">
                <button type="submit" className="w-full px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700">
                  Register DSR Request
                </button>
              </div>
            </form>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Privacy Request Registry</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 border-b">
                  <tr>
                    <th className="p-3">Subject</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Submitted</th>
                    <th className="p-3">Statutory Due</th>
                    <th className="p-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {privacyRequests && privacyRequests.length > 0 ? (
                    privacyRequests.map((p: any) => (
                      <tr key={p.id}>
                        <td className="p-3 font-medium text-gray-900">
                          {p.person_name || p.person_id}
                        </td>
                        <td className="p-3 font-mono text-xs">{p.request_type}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            p.status === "COMPLETED" ? "bg-green-100 text-green-800" :
                            p.status === "REJECTED" ? "bg-red-100 text-red-800" : "bg-blue-100 text-blue-800"
                          }`}>
                            {p.status}
                          </span>
                        </td>
                        <td className="p-3 text-xs text-gray-500">{new Date(p.submitted_at).toLocaleDateString()}</td>
                        <td className="p-3 text-xs font-semibold text-amber-700">{new Date(p.due_at).toLocaleDateString()}</td>
                        <td className="p-3 space-x-2">
                          {(p.request_type === "EXPORT" || p.request_type === "ACCESS") && (
                            <button
                              onClick={() => handleExportPrivacyData(p.id)}
                              className="text-xs text-blue-600 hover:underline font-medium"
                            >
                              Download Export JSON
                            </button>
                          )}
                          {(p.request_type === "DELETION" || p.request_type === "ANONYMIZATION") && p.status !== "COMPLETED" && (
                            <button
                              onClick={() => handleAnonymize(p.id)}
                              className="text-xs text-red-600 hover:underline font-medium"
                            >
                              Execute Erasure
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-4 text-center text-gray-400">No privacy requests logged.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: BCP & DISASTER RECOVERY */}
      {activeTab === "bcp-dr" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
              <h3 className="text-base font-semibold text-gray-900">Disaster Recovery (DR) Thresholds</h3>
              {drPolicies?.map((d: any) => (
                <div key={d.id} className="p-4 rounded border border-gray-100 bg-gray-50 space-y-2">
                  <div className="font-semibold text-gray-900">{d.name}</div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                    <div>RPO Threshold: <strong className="text-gray-900">{d.rpo_minutes} min</strong></div>
                    <div>RTO Threshold: <strong className="text-gray-900">{d.rto_minutes} min</strong></div>
                    <div>Primary Region: <strong className="text-gray-900">{d.primary_region}</strong></div>
                    <div>Recovery Region: <strong className="text-gray-900">{d.recovery_region}</strong></div>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
              <h3 className="text-base font-semibold text-gray-900">Backup Policy Standards</h3>
              {backupPolicies?.map((b: any) => (
                <div key={b.id} className="p-4 rounded border border-gray-100 bg-gray-50 space-y-2">
                  <div className="font-semibold text-gray-900">{b.name}</div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                    <div>Frequency: <strong className="text-gray-900">{b.frequency}</strong></div>
                    <div>Retention: <strong className="text-gray-900">{b.retention_days} days</strong></div>
                    <div>AES-256 Encrypted: <strong className="text-emerald-700">Required</strong></div>
                    <div>Offsite / Cross-Region: <strong className="text-emerald-700">Enforced</strong></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Business Continuity Plans (BCP)</h3>
            <div className="space-y-4">
              {bcpPlans && bcpPlans.length > 0 ? (
                bcpPlans.map((plan: any) => (
                  <div key={plan.id} className="p-4 border border-gray-200 rounded-lg space-y-3">
                    <div className="flex justify-between items-center">
                      <h4 className="font-medium text-gray-900">{plan.name}</h4>
                      <span className="text-xs bg-red-100 text-red-800 font-bold px-2 py-0.5 rounded">{plan.criticality}</span>
                    </div>
                    <p className="text-xs text-gray-600">{plan.recovery_strategy}</p>
                    {plan.actions && plan.actions.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-gray-700">Resumption Step Actions:</div>
                        {plan.actions.map((act: any) => (
                          <div key={act.id} className="text-xs text-gray-600 pl-3 flex justify-between">
                            <span>{act.sequence}. {act.action}</span>
                            <span className="text-gray-400 font-mono">{act.status}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-gray-400 text-sm">No specific continuity plans registered.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 7: DATA RESIDENCY */}
      {activeTab === "residency" && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Sovereign Data Residency Policies</h3>
            <p className="text-xs text-gray-500">
              India Digital Personal Data Protection (DPDP) Act 2023 controls governing cross-border transfers and geographic boundaries.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600 border-b">
                  <tr>
                    <th className="p-3">Data Category</th>
                    <th className="p-3">Primary Region</th>
                    <th className="p-3">Allowed Regions</th>
                    <th className="p-3">Cross-Border Transfer</th>
                    <th className="p-3">Transfer Legal Basis</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {residencyPolicies?.map((res: any) => (
                    <tr key={res.id}>
                      <td className="p-3 font-semibold text-gray-900">{res.data_category}</td>
                      <td className="p-3 font-mono text-xs">{res.primary_region}</td>
                      <td className="p-3 text-xs">{Array.isArray(res.allowed_regions) ? res.allowed_regions.join(", ") : res.allowed_regions}</td>
                      <td className="p-3">
                        {res.cross_border_transfer_allowed ? (
                          <span className="text-xs bg-amber-100 text-amber-800 font-medium px-2 py-0.5 rounded">Permitted with SCC</span>
                        ) : (
                          <span className="text-xs bg-red-100 text-red-800 font-bold px-2 py-0.5 rounded">Prohibited (Sovereign)</span>
                        )}
                      </td>
                      <td className="p-3 text-xs text-gray-500">{res.transfer_basis || "Sovereign Restriction"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
