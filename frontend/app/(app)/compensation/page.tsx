"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function CompensationPage() {
  const { data: overview, mutate: mutateOverview } = useSWR("/v3/compensation/overview", fetcher);
  const { data: structures, mutate: mutateStructures } = useSWR("/v3/compensation/structures", fetcher);
  const { data: revisions, mutate: mutateRevisions } = useSWR("/v3/compensation/revisions", fetcher);
  const { data: bonuses, mutate: mutateBonuses } = useSWR("/v3/compensation/bonuses", fetcher);
  const { data: benefitPlans, mutate: mutatePlans } = useSWR("/v3/benefits/plans", fetcher);
  const { data: enrollments, mutate: mutateEnrollments } = useSWR("/v3/benefits/enrollments", fetcher);

  const [activeTab, setActiveTab] = useState<"overview" | "revisions" | "structures" | "bonuses" | "benefits">("overview");

  // Filter state for revisions
  const [revisionStatusFilter, setRevisionStatusFilter] = useState("all");

  // Modal states
  const [isAddingRevision, setIsAddingRevision] = useState(false);
  const [isAddingBonus, setIsAddingBonus] = useState(false);
  const [isAddingPlan, setIsAddingPlan] = useState(false);
  const [isEnrollingBenefit, setIsEnrollingBenefit] = useState(false);
  const [rejectingRevisionId, setRejectingRevisionId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  // Revision Form State
  const [targetPersonId, setTargetPersonId] = useState("");
  const [newCtcAnnual, setNewCtcAnnual] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().split("T")[0]);
  const [revisionReason, setRevisionReason] = useState("annual_review");
  const [justification, setJustification] = useState("");
  const [hrNotes, setHrNotes] = useState("");

  // Bonus Form State
  const [bonusPersonId, setBonusPersonId] = useState("");
  const [bonusType, setBonusType] = useState("performance");
  const [bonusAmount, setBonusAmount] = useState("");
  const [bonusPayPeriod, setBonusPayPeriod] = useState("2026-10");
  const [bonusDate, setBonusDate] = useState(new Date().toISOString().split("T")[0]);
  const [bonusReason, setBonusReason] = useState("");

  // Plan Form State
  const [planName, setPlanName] = useState("");
  const [planType, setPlanType] = useState("health_insurance");
  const [planProvider, setPlanProvider] = useState("");
  const [planDescription, setPlanDescription] = useState("");
  const [planEmployerContrib, setPlanEmployerContrib] = useState("1200");
  const [planEmployeeDeduct, setPlanEmployeeDeduct] = useState("300");

  // Enrollment Form State
  const [enrollPersonId, setEnrollPersonId] = useState("");
  const [enrollPlanId, setEnrollPlanId] = useState("");
  const [enrollTier, setEnrollTier] = useState("employee_only");
  const [enrollEffectiveDate, setEnrollEffectiveDate] = useState(new Date().toISOString().split("T")[0]);
  const [enrollNotes, setEnrollNotes] = useState("");

  // Handler: Create Revision
  const handleCreateRevision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetPersonId || !newCtcAnnual) return;
    try {
      const annual = parseFloat(newCtcAnnual);
      const monthly = Math.round((annual / 12) * 100) / 100;
      const components = [
        { code: "BASIC", name: "Basic Salary", amount: Math.round(monthly * 0.5), type: "earning" },
        { code: "HRA", name: "House Rent Allowance", amount: Math.round(monthly * 0.3), type: "earning" },
        { code: "SPECIAL", name: "Special Allowance", amount: Math.round(monthly * 0.2), type: "earning" },
      ];

      await api.post("/v3/compensation/revisions", {
        person_id: targetPersonId,
        new_ctc_annual: annual,
        new_ctc_monthly: monthly,
        currency: "INR",
        components_json: components,
        effective_date: effectiveDate,
        reason: revisionReason,
        business_justification: justification || null,
        hr_notes: hrNotes || null,
      });

      alert("Compensation revision proposal submitted successfully.");
      setIsAddingRevision(false);
      setTargetPersonId("");
      setNewCtcAnnual("");
      setJustification("");
      setHrNotes("");
      mutateRevisions();
      mutateOverview();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error submitting compensation revision.");
    }
  };

  // Handler: Approve Revision
  const handleApproveRevision = async (revisionId: string) => {
    if (!confirm("Are you sure you want to approve this compensation revision? This will update the employee's active salary structure.")) return;
    try {
      await api.post(`/v3/compensation/revisions/${revisionId}/approve`);
      alert("Compensation revision approved and salary structure updated.");
      mutateRevisions();
      mutateStructures();
      mutateOverview();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error approving revision.");
    }
  };

  // Handler: Reject Revision
  const handleRejectRevision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectingRevisionId) return;
    try {
      await api.post(`/v3/compensation/revisions/${rejectingRevisionId}/reject`, {
        action: "reject",
        rejection_reason: rejectionReason || "Rejected by compensation reviewer",
      });
      alert("Compensation revision rejected.");
      setRejectingRevisionId(null);
      setRejectionReason("");
      mutateRevisions();
      mutateOverview();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error rejecting revision.");
    }
  };

  // Handler: Create Bonus
  const handleCreateBonus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bonusPersonId || !bonusAmount) return;
    try {
      await api.post("/v3/compensation/bonuses", {
        person_id: bonusPersonId,
        bonus_type: bonusType,
        amount: parseFloat(bonusAmount),
        currency: "INR",
        pay_period: bonusPayPeriod,
        effective_date: bonusDate,
        reason: bonusReason || null,
      });
      alert("Bonus record created.");
      setIsAddingBonus(false);
      setBonusPersonId("");
      setBonusAmount("");
      setBonusReason("");
      mutateBonuses();
      mutateOverview();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error creating bonus.");
    }
  };

  // Handler: Review Bonus (Approve / Reject)
  const handleReviewBonus = async (bonusId: string, action: "approve" | "reject") => {
    try {
      await api.post(`/v3/compensation/bonuses/${bonusId}/review`, { action });
      alert(`Bonus ${action}d successfully.`);
      mutateBonuses();
      mutateOverview();
    } catch (err: any) {
      alert(err?.response?.data?.detail || `Error ${action}ing bonus.`);
    }
  };

  // Handler: Create Plan
  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!planName) return;
    try {
      await api.post("/v3/benefits/plans", {
        name: planName,
        benefit_type: planType,
        provider: planProvider || null,
        description: planDescription || null,
        employer_contribution: parseFloat(planEmployerContrib || "0"),
        employee_deduction: parseFloat(planEmployeeDeduct || "0"),
      });
      alert("Benefit plan created successfully.");
      setIsAddingPlan(false);
      setPlanName("");
      setPlanProvider("");
      setPlanDescription("");
      mutatePlans();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error creating benefit plan.");
    }
  };

  // Handler: Enroll Employee
  const handleEnrollEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enrollPersonId || !enrollPlanId) return;
    try {
      await api.post("/v3/benefits/enroll", {
        person_id: enrollPersonId,
        benefit_plan_id: enrollPlanId,
        coverage_tier: enrollTier,
        effective_date: enrollEffectiveDate,
        notes: enrollNotes || null,
      });
      alert("Employee enrolled in benefit plan.");
      setIsEnrollingBenefit(false);
      setEnrollPersonId("");
      setEnrollPlanId("");
      setEnrollNotes("");
      mutateEnrollments();
      mutateOverview();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error enrolling employee.");
    }
  };

  // Handler: Terminate Enrollment
  const handleTerminateEnrollment = async (enrollmentId: string) => {
    if (!confirm("Are you sure you want to terminate this benefit enrollment?")) return;
    try {
      await api.post(`/v3/benefits/enrollments/${enrollmentId}/terminate`);
      alert("Benefit enrollment terminated.");
      mutateEnrollments();
      mutateOverview();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error terminating enrollment.");
    }
  };

  // Filtered revisions
  const filteredRevisions = (revisions || []).filter((r: any) => {
    if (revisionStatusFilter === "all") return true;
    return r.status === revisionStatusFilter;
  });

  return (
    <div className="space-y-6">
      {/* Page Title & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Compensation & Benefits Management</h2>
          <p className="text-gray-500 text-sm mt-0.5">
            Module 7: Enterprise salary structures, effective-dated revisions, bonuses & corporate benefits.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAddingRevision(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition"
          >
            + New Revision Proposal
          </button>
          <button
            onClick={() => setIsAddingBonus(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition"
          >
            + Award Bonus
          </button>
          <button
            onClick={() => setIsEnrollingBenefit(true)}
            className="bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition"
          >
            + Enroll Benefit
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Active Structures</p>
          <p className="text-xl font-bold text-gray-900 mt-1">{overview?.active_structures_count ?? "—"}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">Assigned employees</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-amber-200 shadow-sm bg-amber-50/20">
          <p className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">Pending Revisions</p>
          <p className="text-xl font-bold text-amber-900 mt-1">{overview?.pending_revisions_count ?? 0}</p>
          <p className="text-[10px] text-amber-600 mt-0.5">Awaiting review</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-emerald-200 shadow-sm bg-emerald-50/20">
          <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">Approved Revisions</p>
          <p className="text-xl font-bold text-emerald-900 mt-1">{overview?.approved_revisions_count ?? 0}</p>
          <p className="text-[10px] text-emerald-600 mt-0.5">Applied / Effective</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-purple-200 shadow-sm bg-purple-50/20">
          <p className="text-[11px] font-semibold text-purple-700 uppercase tracking-wider">Pending Bonuses</p>
          <p className="text-xl font-bold text-purple-900 mt-1">{overview?.pending_bonuses_count ?? 0}</p>
          <p className="text-[10px] text-purple-600 mt-0.5">Awaiting payout</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Annual Payroll</p>
          <p className="text-lg font-bold text-gray-900 mt-1 truncate">
            ₹{overview?.total_annual_payroll_commitment?.toLocaleString() ?? "0"}
          </p>
          <p className="text-[10px] text-gray-500 mt-0.5">CTC commitment</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-blue-200 shadow-sm bg-blue-50/20">
          <p className="text-[11px] font-semibold text-blue-700 uppercase tracking-wider">Benefits Enrolled</p>
          <p className="text-xl font-bold text-blue-900 mt-1">{overview?.total_benefits_enrolled ?? 0}</p>
          <p className="text-[10px] text-blue-600 mt-0.5">Active coverages</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 flex gap-4 text-xs font-semibold">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-2.5 transition border-b-2 ${
            activeTab === "overview" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          📊 Compensation Overview
        </button>
        <button
          onClick={() => setActiveTab("revisions")}
          className={`pb-2.5 transition border-b-2 flex items-center gap-1.5 ${
            activeTab === "revisions" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          📝 Revisions & Approvals
          {overview?.pending_revisions_count > 0 && (
            <span className="bg-amber-100 text-amber-800 text-[10px] px-1.5 py-0.2 rounded-full font-bold">
              {overview.pending_revisions_count}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("structures")}
          className={`pb-2.5 transition border-b-2 ${
            activeTab === "structures" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          💼 Salary Structures
        </button>
        <button
          onClick={() => setActiveTab("bonuses")}
          className={`pb-2.5 transition border-b-2 ${
            activeTab === "bonuses" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          🎁 Bonuses & Incentives
        </button>
        <button
          onClick={() => setActiveTab("benefits")}
          className={`pb-2.5 transition border-b-2 ${
            activeTab === "benefits" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          🛡️ Benefits Management
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
            <h3 className="font-bold text-gray-900 text-sm">Enterprise Compensation Governance</h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              Zeramai Enterprise Compensation & Benefits Management provides auditable, effective-dated salary administration.
              Revisions undergo strict multi-tier review, eliminating unauthorized direct edits and maintaining complete
              historical integrity across employment cycles.
            </p>
            <div className="space-y-2 border-t pt-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500">Effective-Dating Engine:</span>
                <span className="font-semibold text-emerald-600">Active & Automated</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500">Manager Recommendation Scope:</span>
                <span className="font-semibold text-indigo-600">Direct Reports Only</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500">Self-Approval Protection:</span>
                <span className="font-semibold text-emerald-600">Enforced by RBAC</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500">Payroll Integration:</span>
                <span className="font-semibold text-emerald-600">Live with Global Batch Runs</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-gray-900 text-sm">Pending Action Items</h3>
              <span className="text-xs text-indigo-600 font-semibold cursor-pointer" onClick={() => setActiveTab("revisions")}>
                View all →
              </span>
            </div>
            {filteredRevisions.filter((r: any) => r.status === "submitted").length === 0 ? (
              <p className="text-xs text-gray-400 py-6 text-center">No pending compensation revisions awaiting action.</p>
            ) : (
              <div className="space-y-2">
                {filteredRevisions
                  .filter((r: any) => r.status === "submitted")
                  .slice(0, 4)
                  .map((r: any) => (
                    <div key={r.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200 flex justify-between items-center">
                      <div>
                        <p className="text-xs font-semibold text-gray-900">{r.person_name || "Employee"}</p>
                        <p className="text-[11px] text-gray-500">
                          Proposed CTC: ₹{r.new_ctc_annual?.toLocaleString()} • Effective: {r.effective_date}
                        </p>
                      </div>
                      <button
                        onClick={() => handleApproveRevision(r.id)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-semibold px-2.5 py-1 rounded shadow-sm"
                      >
                        Approve
                      </button>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Revisions & Approvals */}
      {activeTab === "revisions" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Status filter:</span>
              <select
                value={revisionStatusFilter}
                onChange={(e) => setRevisionStatusFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded px-2 py-1 bg-white"
              >
                <option value="all">All Revisions</option>
                <option value="submitted">Submitted</option>
                <option value="approved">Approved</option>
                <option value="effective">Effective</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
            <button
              onClick={() => setIsAddingRevision(true)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm"
            >
              + Propose Revision
            </button>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">Employee</th>
                  <th className="px-4 py-3 text-left">Previous CTC</th>
                  <th className="px-4 py-3 text-left">Proposed CTC</th>
                  <th className="px-4 py-3 text-left">Effective Date</th>
                  <th className="px-4 py-3 text-left">Reason</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 text-gray-700">
                {filteredRevisions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                      No compensation revisions found.
                    </td>
                  </tr>
                ) : (
                  filteredRevisions.map((r: any) => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold text-gray-900">{r.person_name || r.person_id}</td>
                      <td className="px-4 py-3 text-gray-500">
                        {r.previous_ctc_annual ? `₹${r.previous_ctc_annual.toLocaleString()}` : "—"}
                      </td>
                      <td className="px-4 py-3 font-bold text-gray-900">₹{r.new_ctc_annual?.toLocaleString()}</td>
                      <td className="px-4 py-3">{r.effective_date}</td>
                      <td className="px-4 py-3 capitalize text-gray-600">{r.reason?.replace("_", " ")}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            r.status === "effective"
                              ? "bg-emerald-100 text-emerald-800"
                              : r.status === "approved"
                              ? "bg-blue-100 text-blue-800"
                              : r.status === "submitted"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        {r.status === "submitted" && (
                          <>
                            <button
                              onClick={() => handleApproveRevision(r.id)}
                              className="text-emerald-600 hover:text-emerald-800 font-semibold"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => setRejectingRevisionId(r.id)}
                              className="text-red-600 hover:text-red-800 font-semibold"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {r.hr_notes && (
                          <span className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono ml-2">
                            HR Note
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

      {/* Tab 3: Salary Structures */}
      {activeTab === "structures" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-200">
            <h3 className="font-bold text-gray-900 text-sm">Active Enterprise Salary Structures</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Current effective baseline structures consumed directly by the monthly payroll calculation engine.
            </p>
          </div>
          <table className="min-w-full divide-y divide-gray-200 text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase font-semibold">
              <tr>
                <th className="px-4 py-3 text-left">Employee</th>
                <th className="px-4 py-3 text-left">Structure Title</th>
                <th className="px-4 py-3 text-left">Effective From</th>
                <th className="px-4 py-3 text-left">Annual CTC</th>
                <th className="px-4 py-3 text-left">Monthly Gross</th>
                <th className="px-4 py-3 text-left">Key Components</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 text-gray-700">
              {(structures || []).length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    No active salary structures recorded.
                  </td>
                </tr>
              ) : (
                (structures || []).map((s: any) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-semibold text-gray-900">{s.person_name || s.person_id}</td>
                    <td className="px-4 py-3 font-mono text-indigo-600">{s.name}</td>
                    <td className="px-4 py-3">{s.effective_from}</td>
                    <td className="px-4 py-3 font-bold text-gray-900">₹{s.ctc_annual?.toLocaleString()}</td>
                    <td className="px-4 py-3">₹{s.ctc_monthly?.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(s.components_json || []).map((c: any, idx: number) => (
                          <span key={idx} className="bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded text-[10px]">
                            {c.code}: ₹{c.amount?.toLocaleString()}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 4: Bonuses & Incentives */}
      {activeTab === "bonuses" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-gray-900 text-sm">Bonuses & Incentive Records</h3>
            <button
              onClick={() => setIsAddingBonus(true)}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm"
            >
              + Award Bonus
            </button>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">Employee</th>
                  <th className="px-4 py-3 text-left">Bonus Type</th>
                  <th className="px-4 py-3 text-left">Amount</th>
                  <th className="px-4 py-3 text-left">Pay Period</th>
                  <th className="px-4 py-3 text-left">Reason</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Payroll Integration</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 text-gray-700">
                {(bonuses || []).length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                      No bonus records found.
                    </td>
                  </tr>
                ) : (
                  (bonuses || []).map((b: any) => (
                    <tr key={b.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold text-gray-900">{b.person_name || b.person_id}</td>
                      <td className="px-4 py-3 capitalize">{b.bonus_type?.replace("_", " ")}</td>
                      <td className="px-4 py-3 font-bold text-emerald-700">₹{b.amount?.toLocaleString()}</td>
                      <td className="px-4 py-3 font-mono">{b.pay_period}</td>
                      <td className="px-4 py-3 text-gray-500 truncate max-w-xs">{b.reason || "—"}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            b.status === "approved"
                              ? "bg-emerald-100 text-emerald-800"
                              : b.status === "submitted"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {b.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            b.payroll_status === "processed"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {b.payroll_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        {b.status === "submitted" && (
                          <>
                            <button
                              onClick={() => handleReviewBonus(b.id, "approve")}
                              className="text-emerald-600 hover:text-emerald-800 font-semibold"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleReviewBonus(b.id, "reject")}
                              className="text-red-600 hover:text-red-800 font-semibold"
                            >
                              Reject
                            </button>
                          </>
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

      {/* Tab 5: Benefits Management */}
      {activeTab === "benefits" && (
        <div className="space-y-6">
          {/* Plans Section */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-900 text-sm">Configured Corporate Benefit Plans</h3>
                <p className="text-xs text-gray-500">Health, life, wellness, and company sponsored coverage plans.</p>
              </div>
              <button
                onClick={() => setIsAddingPlan(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm"
              >
                + Create Benefit Plan
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {(benefitPlans || []).map((p: any) => (
                <div key={p.id} className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-2">
                  <div className="flex justify-between items-start">
                    <h4 className="font-bold text-gray-900 text-xs">{p.name}</h4>
                    <span className="text-[10px] bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded font-bold uppercase">
                      {p.benefit_type?.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">{p.provider || "Direct Employer Benefit"}</p>
                  <div className="border-t pt-2 flex justify-between text-[11px] text-gray-600">
                    <span>Company: ₹{p.employer_contribution}</span>
                    <span>Employee: ₹{p.employee_deduction}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Enrollments Section */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-900 text-sm">Active Employee Benefit Enrollments</h3>
                <p className="text-xs text-gray-500">Track coverage tiers, deduction contributions, and tenure.</p>
              </div>
              <button
                onClick={() => setIsEnrollingBenefit(true)}
                className="bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm"
              >
                + Enroll Employee
              </button>
            </div>
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">Employee</th>
                  <th className="px-4 py-3 text-left">Benefit Plan</th>
                  <th className="px-4 py-3 text-left">Coverage Tier</th>
                  <th className="px-4 py-3 text-left">Employer Contrib.</th>
                  <th className="px-4 py-3 text-left">Employee Contrib.</th>
                  <th className="px-4 py-3 text-left">Effective Date</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 text-gray-700">
                {(enrollments || []).length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                      No active benefit enrollments recorded.
                    </td>
                  </tr>
                ) : (
                  (enrollments || []).map((e: any) => (
                    <tr key={e.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold text-gray-900">{e.person_name || e.person_id}</td>
                      <td className="px-4 py-3 font-medium text-indigo-600">{e.plan_name}</td>
                      <td className="px-4 py-3 capitalize">{e.coverage_tier?.replace("_", " ")}</td>
                      <td className="px-4 py-3">₹{e.employer_contribution}</td>
                      <td className="px-4 py-3">₹{e.employee_contribution}</td>
                      <td className="px-4 py-3">{e.effective_date}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            e.status === "enrolled" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                          }`}
                        >
                          {e.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {e.status === "enrolled" && (
                          <button
                            onClick={() => handleTerminateEnrollment(e.id)}
                            className="text-red-600 hover:text-red-800 font-semibold"
                          >
                            Terminate
                          </button>
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

      {/* Modal: New Revision Proposal */}
      {isAddingRevision && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="font-bold text-gray-900 text-base">Propose Compensation Revision</h3>
            <form onSubmit={handleCreateRevision} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Employee Person ID *</label>
                <input
                  type="text"
                  required
                  placeholder="UUID of employee"
                  value={targetPersonId}
                  onChange={(e) => setTargetPersonId(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 font-mono"
                />
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Proposed Annual CTC (INR) *</label>
                <input
                  type="number"
                  required
                  placeholder="e.g. 1500000"
                  value={newCtcAnnual}
                  onChange={(e) => setNewCtcAnnual(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Effective Date *</label>
                  <input
                    type="date"
                    required
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Revision Reason</label>
                  <select
                    value={revisionReason}
                    onChange={(e) => setRevisionReason(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
                  >
                    <option value="annual_review">Annual Review</option>
                    <option value="promotion">Promotion</option>
                    <option value="market_adjustment">Market Adjustment</option>
                    <option value="retention">Retention</option>
                    <option value="probation_confirmation">Probation Confirmation</option>
                    <option value="ad_hoc">Ad Hoc</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Business Justification</label>
                <textarea
                  rows={2}
                  placeholder="Reason for compensation revision..."
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Confidential HR Notes (HR-Only)</label>
                <textarea
                  rows={2}
                  placeholder="Private internal notes, hidden from employee..."
                  value={hrNotes}
                  onChange={(e) => setHrNotes(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setIsAddingRevision(false)}
                  className="px-3 py-2 rounded text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded font-semibold">
                  Submit Proposal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Award Bonus */}
      {isAddingBonus && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="font-bold text-gray-900 text-base">Award Employee Bonus / Incentive</h3>
            <form onSubmit={handleCreateBonus} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Employee Person ID *</label>
                <input
                  type="text"
                  required
                  placeholder="UUID of employee"
                  value={bonusPersonId}
                  onChange={(e) => setBonusPersonId(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Bonus Type</label>
                  <select
                    value={bonusType}
                    onChange={(e) => setBonusType(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
                  >
                    <option value="performance">Performance Bonus</option>
                    <option value="retention">Retention Bonus</option>
                    <option value="sales_incentive">Sales Incentive</option>
                    <option value="spot_award">Spot Award</option>
                    <option value="annual">Annual Bonus</option>
                    <option value="signing">Signing Bonus</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Amount (INR) *</label>
                  <input
                    type="number"
                    required
                    placeholder="e.g. 50000"
                    value={bonusAmount}
                    onChange={(e) => setBonusAmount(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Pay Period (YYYY-MM) *</label>
                  <input
                    type="text"
                    required
                    placeholder="2026-10"
                    value={bonusPayPeriod}
                    onChange={(e) => setBonusPayPeriod(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Effective Date</label>
                  <input
                    type="date"
                    required
                    value={bonusDate}
                    onChange={(e) => setBonusDate(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  />
                </div>
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Reason / Citation</label>
                <textarea
                  rows={2}
                  placeholder="Achievement or award justification..."
                  value={bonusReason}
                  onChange={(e) => setBonusReason(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setIsAddingBonus(false)}
                  className="px-3 py-2 rounded text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button type="submit" className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-semibold">
                  Record Bonus
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create Benefit Plan */}
      {isAddingPlan && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="font-bold text-gray-900 text-base">Create Benefit Plan</h3>
            <form onSubmit={handleCreatePlan} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Plan Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Executive Health Floater 10L"
                  value={planName}
                  onChange={(e) => setPlanName(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Benefit Type</label>
                  <select
                    value={planType}
                    onChange={(e) => setPlanType(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
                  >
                    <option value="health_insurance">Health Insurance</option>
                    <option value="life_insurance">Life Insurance</option>
                    <option value="retirement">Retirement / Pension</option>
                    <option value="wellness">Wellness & Gym</option>
                    <option value="meal_benefit">Meal / Food Card</option>
                    <option value="transport">Transport / Commute</option>
                    <option value="other">Other Benefit</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Provider</label>
                  <input
                    type="text"
                    placeholder="e.g. Star Health"
                    value={planProvider}
                    onChange={(e) => setPlanProvider(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Employer Contribution</label>
                  <input
                    type="number"
                    value={planEmployerContrib}
                    onChange={(e) => setPlanEmployerContrib(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Employee Deduction</label>
                  <input
                    type="number"
                    value={planEmployeeDeduct}
                    onChange={(e) => setPlanEmployeeDeduct(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  />
                </div>
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Plan summary and coverage details..."
                  value={planDescription}
                  onChange={(e) => setPlanDescription(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setIsAddingPlan(false)}
                  className="px-3 py-2 rounded text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded font-semibold">
                  Save Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Enroll Benefit */}
      {isEnrollingBenefit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="font-bold text-gray-900 text-base">Enroll Employee in Benefit Plan</h3>
            <form onSubmit={handleEnrollEmployee} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Employee Person ID *</label>
                <input
                  type="text"
                  required
                  placeholder="UUID of employee"
                  value={enrollPersonId}
                  onChange={(e) => setEnrollPersonId(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 font-mono"
                />
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Benefit Plan *</label>
                <select
                  required
                  value={enrollPlanId}
                  onChange={(e) => setEnrollPlanId(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
                >
                  <option value="">Select a benefit plan...</option>
                  {(benefitPlans || []).map((p: any) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.benefit_type})
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Coverage Tier</label>
                  <select
                    value={enrollTier}
                    onChange={(e) => setEnrollTier(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
                  >
                    <option value="employee_only">Employee Only</option>
                    <option value="employee_and_spouse">Employee + Spouse</option>
                    <option value="family_floater">Family Floater</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">Effective Date</label>
                  <input
                    type="date"
                    required
                    value={enrollEffectiveDate}
                    onChange={(e) => setEnrollEffectiveDate(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                  />
                </div>
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Notes</label>
                <textarea
                  rows={2}
                  placeholder="Enrollment remarks..."
                  value={enrollNotes}
                  onChange={(e) => setEnrollNotes(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setIsEnrollingBenefit(false)}
                  className="px-3 py-2 rounded text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button type="submit" className="px-4 py-2 bg-slate-900 hover:bg-black text-white rounded font-semibold">
                  Confirm Enrollment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Reject Revision */}
      {rejectingRevisionId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-5 space-y-3">
            <h3 className="font-bold text-gray-900 text-sm">Reject Compensation Revision</h3>
            <form onSubmit={handleRejectRevision} className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-700 font-semibold mb-1">Rejection Reason *</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Reason for revision rejection..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setRejectingRevisionId(null)}
                  className="px-3 py-1.5 rounded text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button type="submit" className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded font-semibold">
                  Confirm Rejection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
