"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function FinancePage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "cost-centers" | "gl-accounts" | "journals" | "workforce-cost" | "budget-variance" | "vendors" | "export"
  >("overview");

  // Data fetching
  const { data: dashboard, mutate: mutateDashboard } = useSWR("/api/v3/finance/dashboard", fetcher);
  const { data: costCenters, mutate: mutateCostCenters } = useSWR("/api/v3/finance/cost-centers", fetcher);
  const { data: dimensions } = useSWR("/api/v3/finance/dimensions", fetcher);
  const { data: glAccounts, mutate: mutateGL } = useSWR("/api/v3/finance/gl-accounts", fetcher);
  const { data: glMappings, mutate: mutateMappings } = useSWR("/api/v3/finance/gl-mappings", fetcher);
  const { data: journals, mutate: mutateJournals } = useSWR("/api/v3/finance/payroll-journals", fetcher);
  const { data: workforceCosts, mutate: mutateWorkforceCosts } = useSWR("/api/v3/finance/workforce-costs", fetcher);
  const { data: budgets, mutate: mutateBudgets } = useSWR("/api/v3/finance/budgets", fetcher);
  const { data: vendors, mutate: mutateVendors } = useSWR("/api/v3/finance/vendors", fetcher);
  const { data: invoices, mutate: mutateInvoices } = useSWR("/api/v3/finance/invoices", fetcher);

  // Form states
  const [newCCCode, setNewCCCode] = useState("");
  const [newCCName, setNewCCName] = useState("");
  const [newCCDesc, setNewCCDesc] = useState("");
  const [newCCParent, setNewCCParent] = useState("");
  const [submittingCC, setSubmittingCC] = useState(false);

  const [newGLCode, setNewGLCode] = useState("");
  const [newGLName, setNewGLName] = useState("");
  const [newGLType, setNewGLType] = useState("EXPENSE");
  const [newGLBalance, setNewGLBalance] = useState("DEBIT");
  const [submittingGL, setSubmittingGL] = useState(false);

  const [newVendorName, setNewVendorName] = useState("");
  const [newVendorCategory, setNewVendorCategory] = useState("BENEFITS_PROVIDER");
  const [newVendorContact, setNewVendorContact] = useState("");
  const [newVendorEmail, setNewVendorEmail] = useState("");
  const [submittingVendor, setSubmittingVendor] = useState(false);

  const [exportJournalId, setExportJournalId] = useState("");
  const [exportFormat, setExportFormat] = useState("CSV");
  const [exportOutput, setExportOutput] = useState<string | null>(null);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Handlers
  const handleCreateCostCenter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCCCode || !newCCName) return;
    setSubmittingCC(true);
    try {
      await api.post("/api/v3/finance/cost-centers", {
        code: newCCCode,
        name: newCCName,
        description: newCCDesc || null,
        parent_cost_center_id: newCCParent || null,
        currency: "INR",
        active: true,
      });
      setNewCCCode("");
      setNewCCName("");
      setNewCCDesc("");
      setNewCCParent("");
      setStatusMessage("Cost center created successfully");
      mutateCostCenters();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating cost center");
    } finally {
      setSubmittingCC(false);
    }
  };

  const handleCreateGLAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGLCode || !newGLName) return;
    setSubmittingGL(true);
    try {
      await api.post("/api/v3/finance/gl-accounts", {
        account_code: newGLCode,
        account_name: newGLName,
        account_type: newGLType,
        normal_balance: newGLBalance,
        is_active: true,
      });
      setNewGLCode("");
      setNewGLName("");
      setStatusMessage("GL account created successfully");
      mutateGL();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating GL account");
    } finally {
      setSubmittingGL(false);
    }
  };

  const handleCreateVendor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newVendorName) return;
    setSubmittingVendor(true);
    try {
      await api.post("/api/v3/finance/vendors", {
        name: newVendorName,
        category: newVendorCategory,
        contact_person: newVendorContact || null,
        email: newVendorEmail || null,
        is_active: true,
      });
      setNewVendorName("");
      setNewVendorContact("");
      setNewVendorEmail("");
      setStatusMessage("Vendor registered successfully");
      mutateVendors();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating vendor");
    } finally {
      setSubmittingVendor(false);
    }
  };

  const handleApproveJournal = async (journalId: string) => {
    try {
      await api.post(`/api/v3/finance/payroll-journals/${journalId}/approve`, {});
      setStatusMessage(`Journal ${journalId.slice(0, 8)} approved`);
      mutateJournals();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error approving journal");
    }
  };

  const handlePostJournal = async (journalId: string) => {
    try {
      await api.post(`/api/v3/finance/payroll-journals/${journalId}/post`, {});
      setStatusMessage(`Journal ${journalId.slice(0, 8)} successfully posted to GL`);
      mutateJournals();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error posting journal");
    }
  };

  const handleReverseJournal = async (journalId: string) => {
    const reason = prompt("Enter reversal reason (e.g., 'Correction for payroll run revision'):");
    if (!reason) return;
    try {
      const res = await api.post(`/api/v3/finance/payroll-journals/${journalId}/reverse`, { reason });
      setStatusMessage(`Reversal journal ${res.data.reversal_journal_number} created with balanced inverse lines.`);
      mutateJournals();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error reversing journal");
    }
  };

  const handleExportJournal = async () => {
    if (!exportJournalId) {
      alert("Please select a journal to export");
      return;
    }
    try {
      const res = await api.get(`/api/v3/finance/payroll-journals/${exportJournalId}/export?export_format=${exportFormat}`);
      if (exportFormat === "CSV") {
        setExportOutput(res.data.csv_data);
      } else {
        setExportOutput(JSON.stringify(res.data, null, 2));
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error exporting journal");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <span>🏛️</span> Enterprise Finance & Workforce Cost Management
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Cost center accounting, double-entry payroll journals, workforce cost attribution, budget variance, and vendor invoices.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            Double-Entry Balanced
          </span>
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
            GL Integrated
          </span>
        </div>
      </div>

      {/* Status banner */}
      {statusMessage && (
        <div className="p-3 bg-indigo-50 border border-indigo-200 text-indigo-800 dark:bg-indigo-950/60 dark:border-indigo-800 dark:text-indigo-200 text-xs rounded-lg flex items-center justify-between">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="text-indigo-500 hover:text-indigo-700 font-bold ml-2">✕</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-1 border-b border-slate-200 dark:border-slate-800 overflow-x-auto pb-1">
        {[
          { id: "overview", label: "Overview & Metrics" },
          { id: "cost-centers", label: "Cost Centers & Dimensions" },
          { id: "gl-accounts", label: "GL Accounts & Mappings" },
          { id: "journals", label: "Payroll Journals" },
          { id: "workforce-cost", label: "Workforce Cost" },
          { id: "budget-variance", label: "Budgets & Variance" },
          { id: "vendors", label: "Vendors & Invoices" },
          { id: "export", label: "ERP Export" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg transition whitespace-nowrap ${
              activeTab === tab.id
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Cost Centers</span>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
                {dashboard?.cost_centers_count ?? costCenters?.length ?? 0}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">Hierarchical cost allocations</p>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Workforce Cost</span>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
                ₹{((dashboard?.total_workforce_cost_ytd || 0) / 100000).toFixed(2)}L
              </p>
              <p className="text-[11px] text-slate-500 mt-1">Base, bonuses, statutory & benefits</p>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Balanced Journals</span>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-2">
                {dashboard?.posted_journals_count ?? 0}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">Debit == Credit invariant enforced</p>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Vendors</span>
              <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-2">
                {vendors?.length ?? 0}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">Benefit & recruitment suppliers</p>
            </div>
          </div>

          {/* Quick Summary Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3 flex items-center justify-between">
                <span>Recent Payroll Journals</span>
                <button onClick={() => setActiveTab("journals")} className="text-xs text-indigo-600 hover:underline">View All →</button>
              </h3>
              <div className="space-y-2">
                {(!journals || journals.length === 0) ? (
                  <p className="text-xs text-slate-500 py-3">No payroll journals generated yet.</p>
                ) : (
                  journals.slice(0, 5).map((j: any) => (
                    <div key={j.id} className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-xs">
                      <div>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{j.journal_number}</span>
                        <span className="text-[10px] text-slate-500 ml-2">Period: {j.period_key}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-700 dark:text-slate-300">₹{parseFloat(j.total_debit).toLocaleString()}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          j.status === "POSTED" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" :
                          j.status === "APPROVED" ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300" :
                          j.status === "REVERSED" ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" :
                          "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300"
                        }`}>
                          {j.status}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3 flex items-center justify-between">
                <span>Cost Center Highlights</span>
                <button onClick={() => setActiveTab("cost-centers")} className="text-xs text-indigo-600 hover:underline">Manage →</button>
              </h3>
              <div className="space-y-2">
                {(!costCenters || costCenters.length === 0) ? (
                  <p className="text-xs text-slate-500 py-3">No cost centers found.</p>
                ) : (
                  costCenters.slice(0, 5).map((cc: any) => (
                    <div key={cc.id} className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-xs">
                      <div>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{cc.code}</span>
                        <span className="text-slate-500 ml-2">{cc.name}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">{cc.currency}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: COST CENTERS & DIMENSIONS */}
      {activeTab === "cost-centers" && (
        <div className="space-y-6">
          {/* Create Cost Center Form */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Add Cost Center</h3>
            <form onSubmit={handleCreateCostCenter} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Cost Center Code</label>
                <input
                  type="text"
                  placeholder="e.g., CC-ENG-02"
                  value={newCCCode}
                  onChange={(e) => setNewCCCode(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  required
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Name</label>
                <input
                  type="text"
                  placeholder="e.g., Mobile Apps Engineering"
                  value={newCCName}
                  onChange={(e) => setNewCCName(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  required
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Parent Cost Center (Optional)</label>
                <select
                  value={newCCParent}
                  onChange={(e) => setNewCCParent(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="">None (Top Level)</option>
                  {costCenters?.map((cc: any) => (
                    <option key={cc.id} value={cc.id}>{cc.code} - {cc.name}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={submittingCC}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold py-2 px-4 rounded-lg transition"
                >
                  {submittingCC ? "Saving..." : "Create Cost Center"}
                </button>
              </div>
            </form>
          </div>

          {/* Cost Centers Table */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Active Cost Center Catalog</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4">Code</th>
                    <th className="py-2.5 px-4">Name</th>
                    <th className="py-2.5 px-4">Description</th>
                    <th className="py-2.5 px-4">Currency</th>
                    <th className="py-2.5 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {costCenters?.map((cc: any) => (
                    <tr key={cc.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="py-2.5 px-4 font-mono font-semibold text-slate-800 dark:text-slate-200">{cc.code}</td>
                      <td className="py-2.5 px-4 text-slate-900 dark:text-white font-medium">{cc.name}</td>
                      <td className="py-2.5 px-4 text-slate-500">{cc.description || "—"}</td>
                      <td className="py-2.5 px-4 font-mono">{cc.currency}</td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          Active
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Financial Dimensions Section */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Configured Financial Dimensions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {dimensions?.map((dim: any) => (
                <div key={dim.id} className="border border-slate-200 dark:border-slate-800 rounded-lg p-3 bg-slate-50 dark:bg-slate-800/50">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-slate-800 dark:text-slate-200">{dim.code}</span>
                    <span className="text-[10px] text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded font-semibold">Active</span>
                  </div>
                  <p className="text-xs font-medium text-slate-700 dark:text-slate-300 mt-1">{dim.name}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">{dim.description || "Multi-dimensional financial tagging"}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: GL ACCOUNTS & MAPPINGS */}
      {activeTab === "gl-accounts" && (
        <div className="space-y-6">
          {/* Create GL Account Form */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Add General Ledger (GL) Account</h3>
            <form onSubmit={handleCreateGLAccount} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Account Code</label>
                <input
                  type="text"
                  placeholder="e.g., 50550"
                  value={newGLCode}
                  onChange={(e) => setNewGLCode(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  required
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Account Name</label>
                <input
                  type="text"
                  placeholder="e.g., Wellness Stipend Expense"
                  value={newGLName}
                  onChange={(e) => setNewGLName(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  required
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Type</label>
                <select
                  value={newGLType}
                  onChange={(e) => setNewGLType(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="EXPENSE">EXPENSE</option>
                  <option value="LIABILITY">LIABILITY</option>
                  <option value="ASSET">ASSET</option>
                  <option value="EQUITY">EQUITY</option>
                  <option value="REVENUE">REVENUE</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Normal Balance</label>
                <select
                  value={newGLBalance}
                  onChange={(e) => setNewGLBalance(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="DEBIT">DEBIT</option>
                  <option value="CREDIT">CREDIT</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={submittingGL}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold py-2 px-4 rounded-lg transition"
                >
                  {submittingGL ? "Saving..." : "Add GL Account"}
                </button>
              </div>
            </form>
          </div>

          {/* GL Accounts Table */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Chart of Accounts (COA)</h3>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold sticky top-0">
                    <tr>
                      <th className="py-2.5 px-4">Code</th>
                      <th className="py-2.5 px-4">Account Name</th>
                      <th className="py-2.5 px-4">Type</th>
                      <th className="py-2.5 px-4">Normal Bal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {glAccounts?.map((gl: any) => (
                      <tr key={gl.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-mono font-bold text-slate-800 dark:text-slate-200">{gl.account_code}</td>
                        <td className="py-2.5 px-4 text-slate-900 dark:text-white font-medium">{gl.account_name}</td>
                        <td className="py-2.5 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            gl.account_type === "EXPENSE" ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300" :
                            gl.account_type === "LIABILITY" ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" :
                            "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                          }`}>
                            {gl.account_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 font-mono text-[11px]">{gl.normal_balance}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Payroll Component GL Mappings</h3>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold sticky top-0">
                    <tr>
                      <th className="py-2.5 px-4">Component</th>
                      <th className="py-2.5 px-4">Debit Account</th>
                      <th className="py-2.5 px-4">Credit Account</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {glMappings?.map((m: any) => (
                      <tr key={m.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-medium text-slate-800 dark:text-slate-200">{m.component_type}</td>
                        <td className="py-2.5 px-4 font-mono text-emerald-600 dark:text-emerald-400">{m.debit_gl_account_id ? "Mapped (DR)" : "—"}</td>
                        <td className="py-2.5 px-4 font-mono text-indigo-600 dark:text-indigo-400">{m.credit_gl_account_id ? "Mapped (CR)" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: PAYROLL JOURNALS */}
      {activeTab === "journals" && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Double-Entry Payroll Accounting Journals</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Strict double-entry balance invariant: Total Debits == Total Credits</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4">Journal #</th>
                    <th className="py-2.5 px-4">Period</th>
                    <th className="py-2.5 px-4">Posting Date</th>
                    <th className="py-2.5 px-4">Total Debit</th>
                    <th className="py-2.5 px-4">Total Credit</th>
                    <th className="py-2.5 px-4">Balance Status</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {journals?.map((j: any) => {
                    const isBalanced = Math.abs(parseFloat(j.total_debit) - parseFloat(j.total_credit)) < 0.001;
                    return (
                      <tr key={j.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-mono font-bold text-slate-900 dark:text-white">{j.journal_number}</td>
                        <td className="py-2.5 px-4 font-mono">{j.period_key}</td>
                        <td className="py-2.5 px-4">{j.posting_date}</td>
                        <td className="py-2.5 px-4 font-mono text-emerald-600 dark:text-emerald-400">₹{parseFloat(j.total_debit).toLocaleString()}</td>
                        <td className="py-2.5 px-4 font-mono text-indigo-600 dark:text-indigo-400">₹{parseFloat(j.total_credit).toLocaleString()}</td>
                        <td className="py-2.5 px-4">
                          {isBalanced ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                              Balanced ✓
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">
                              Imbalanced ✕
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            j.status === "POSTED" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" :
                            j.status === "APPROVED" ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300" :
                            j.status === "REVERSED" ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" :
                            "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300"
                          }`}>
                            {j.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 space-x-1.5 whitespace-nowrap">
                          {j.status === "DRAFT" && (
                            <button
                              onClick={() => handleApproveJournal(j.id)}
                              className="px-2 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-[10px] font-semibold transition"
                            >
                              Approve
                            </button>
                          )}
                          {j.status === "APPROVED" && (
                            <button
                              onClick={() => handlePostJournal(j.id)}
                              className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[10px] font-semibold transition"
                            >
                              Post to GL
                            </button>
                          )}
                          {j.status === "POSTED" && (
                            <button
                              onClick={() => handleReverseJournal(j.id)}
                              className="px-2 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-[10px] font-semibold transition"
                            >
                              Reverse
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: WORKFORCE COST */}
      {activeTab === "workforce-cost" && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Normalized Workforce Cost Attribution</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">Fully loaded cost per employee and cost center (Gross + Employer Statutory + Benefits + Expenses)</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4">Period</th>
                    <th className="py-2.5 px-4">Cost Center</th>
                    <th className="py-2.5 px-4">Base Salary</th>
                    <th className="py-2.5 px-4">Bonus</th>
                    <th className="py-2.5 px-4">Employer Statutory</th>
                    <th className="py-2.5 px-4">Benefits</th>
                    <th className="py-2.5 px-4">Total Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {workforceCosts?.map((wc: any) => (
                    <tr key={wc.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="py-2.5 px-4 font-mono">{wc.period_key}</td>
                      <td className="py-2.5 px-4 font-semibold text-slate-800 dark:text-slate-200">{wc.cost_center_code || wc.cost_center_id?.slice(0, 8)}</td>
                      <td className="py-2.5 px-4 font-mono">₹{parseFloat(wc.base_salary_amount).toLocaleString()}</td>
                      <td className="py-2.5 px-4 font-mono">₹{parseFloat(wc.bonus_amount).toLocaleString()}</td>
                      <td className="py-2.5 px-4 font-mono">₹{parseFloat(wc.employer_statutory_amount).toLocaleString()}</td>
                      <td className="py-2.5 px-4 font-mono">₹{parseFloat(wc.benefits_amount).toLocaleString()}</td>
                      <td className="py-2.5 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">₹{parseFloat(wc.total_cost).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: BUDGETS & VARIANCE */}
      {activeTab === "budget-variance" && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Workforce Budgets & Actuals</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4">Budget Name</th>
                    <th className="py-2.5 px-4">Fiscal Year</th>
                    <th className="py-2.5 px-4">Allocated Headcount</th>
                    <th className="py-2.5 px-4">Total Budget Amount</th>
                    <th className="py-2.5 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {budgets?.map((b: any) => (
                    <tr key={b.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="py-2.5 px-4 font-medium text-slate-900 dark:text-white">{b.name}</td>
                      <td className="py-2.5 px-4 font-mono">{b.fiscal_year}</td>
                      <td className="py-2.5 px-4 font-mono">{b.headcount_target || "—"}</td>
                      <td className="py-2.5 px-4 font-mono font-bold">₹{parseFloat(b.total_budget_amount || 0).toLocaleString()}</td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          {b.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 7: VENDORS & INVOICES */}
      {activeTab === "vendors" && (
        <div className="space-y-6">
          {/* Add Vendor Form */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Register Vendor / Supplier</h3>
            <form onSubmit={handleCreateVendor} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Vendor Name</label>
                <input
                  type="text"
                  placeholder="e.g., Star Health Insurance Ltd"
                  value={newVendorName}
                  onChange={(e) => setNewVendorName(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  required
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Category</label>
                <select
                  value={newVendorCategory}
                  onChange={(e) => setNewVendorCategory(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="BENEFITS_PROVIDER">BENEFITS_PROVIDER</option>
                  <option value="STAFFING_AGENCY">STAFFING_AGENCY</option>
                  <option value="SOFTWARE_SAAS">SOFTWARE_SAAS</option>
                  <option value="CONSULTING">CONSULTING</option>
                  <option value="GENERAL">GENERAL</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Contact Person</label>
                <input
                  type="text"
                  placeholder="e.g., Rajesh Kumar"
                  value={newVendorContact}
                  onChange={(e) => setNewVendorContact(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Email</label>
                <input
                  type="email"
                  placeholder="e.g., billing@starhealth.in"
                  value={newVendorEmail}
                  onChange={(e) => setNewVendorEmail(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={submittingVendor}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold py-2 px-4 rounded-lg transition"
                >
                  {submittingVendor ? "Saving..." : "Add Vendor"}
                </button>
              </div>
            </form>
          </div>

          {/* Vendors & Invoices Tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Vendor Directory</h3>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold sticky top-0">
                    <tr>
                      <th className="py-2.5 px-4">Name</th>
                      <th className="py-2.5 px-4">Category</th>
                      <th className="py-2.5 px-4">Contact</th>
                      <th className="py-2.5 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {vendors?.map((v: any) => (
                      <tr key={v.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-semibold text-slate-900 dark:text-white">{v.name}</td>
                        <td className="py-2.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
                            {v.category}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-500">{v.email || v.contact_person || "—"}</td>
                        <td className="py-2.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                            Active
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Vendor Invoices</h3>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-xs text-slate-600 dark:text-slate-400">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold sticky top-0">
                    <tr>
                      <th className="py-2.5 px-4">Invoice #</th>
                      <th className="py-2.5 px-4">Amount</th>
                      <th className="py-2.5 px-4">Due Date</th>
                      <th className="py-2.5 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {invoices?.map((inv: any) => (
                      <tr key={inv.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-mono font-bold text-slate-900 dark:text-white">{inv.invoice_number}</td>
                        <td className="py-2.5 px-4 font-mono">₹{parseFloat(inv.total_amount).toLocaleString()}</td>
                        <td className="py-2.5 px-4">{inv.due_date}</td>
                        <td className="py-2.5 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            inv.status === "PAID" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" :
                            inv.status === "APPROVED" ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300" :
                            "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300"
                          }`}>
                            {inv.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 8: ACCOUNTING EXPORT */}
      {activeTab === "export" && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-2">Accounting Journal Export</h3>
            <p className="text-xs text-slate-500 mb-4">Export balanced double-entry payroll journals to standard CSV or JSON for ERP ingestion (SAP S/4HANA, Oracle NetSuite, Tally Prime).</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Select Journal</label>
                <select
                  value={exportJournalId}
                  onChange={(e) => setExportJournalId(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="">Select Journal...</option>
                  {journals?.map((j: any) => (
                    <option key={j.id} value={j.id}>{j.journal_number} ({j.period_key}) - ₹{parseFloat(j.total_debit).toLocaleString()}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">Export Format</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="CSV">Standard ERP CSV</option>
                  <option value="JSON">Generic Accounting JSON</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleExportJournal}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold py-2 px-4 rounded-lg transition"
                >
                  Generate Export
                </button>
              </div>
            </div>

            {exportOutput && (
              <div className="mt-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Export Preview:</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(exportOutput);
                      alert("Copied to clipboard!");
                    }}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    Copy to Clipboard
                  </button>
                </div>
                <pre className="p-3 bg-slate-900 text-emerald-400 font-mono text-xs rounded-lg overflow-x-auto max-h-80 border border-slate-800">
                  {exportOutput}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
