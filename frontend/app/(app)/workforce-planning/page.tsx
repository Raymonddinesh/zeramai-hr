"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function WorkforcePlanningPage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "org-units" | "positions" | "headcount" | "skills" | "succession" | "scenarios" | "mobility"
  >("overview");

  // Data fetching
  const { data: dashboard, mutate: mutateDashboard } = useSWR("/api/v3/workforce-planning/dashboard", fetcher);
  const { data: orgUnits, mutate: mutateOrgUnits } = useSWR("/api/v3/workforce-planning/organization-units?as_tree=false", fetcher);
  const { data: positions, mutate: mutatePositions } = useSWR("/api/v3/workforce-planning/positions", fetcher);
  const { data: headcountPlans, mutate: mutatePlans } = useSWR("/api/v3/workforce-planning/headcount-plans", fetcher);
  const { data: skills, mutate: mutateSkills } = useSWR("/api/v3/workforce-planning/skills", fetcher);
  const { data: criticalRoles, mutate: mutateCriticalRoles } = useSWR("/api/v3/workforce-planning/critical-roles", fetcher);
  const { data: successionPlans, mutate: mutateSuccession } = useSWR("/api/v3/workforce-planning/succession-plans", fetcher);
  const { data: talentPools, mutate: mutatePools } = useSWR("/api/v3/workforce-planning/talent-pools", fetcher);
  const { data: scenarios, mutate: mutateScenarios } = useSWR("/api/v3/workforce-planning/scenarios", fetcher);
  const { data: hiringPlans, mutate: mutateHiringPlans } = useSWR("/api/v3/workforce-planning/hiring-plans", fetcher);
  const { data: mobilityPlans, mutate: mutateMobility } = useSWR("/api/v3/workforce-planning/mobility-plans", fetcher);

  // Form states
  const [newOrgCode, setNewOrgCode] = useState("");
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgParent, setNewOrgParent] = useState("");
  const [submittingOrg, setSubmittingOrg] = useState(false);

  const [newPosCode, setNewPosCode] = useState("");
  const [newPosTitle, setNewPosTitle] = useState("");
  const [newPosOrg, setNewPosOrg] = useState("");
  const [newPosLevel, setNewPosLevel] = useState("L3_SENIOR");
  const [newPosCapacity, setNewPosCapacity] = useState(1.0);
  const [newPosCost, setNewPosCost] = useState(1200000);
  const [submittingPos, setSubmittingPos] = useState(false);

  const [newPlanName, setNewPlanName] = useState("");
  const [newPlanYear, setNewPlanYear] = useState("2026-2027");
  const [submittingPlan, setSubmittingPlan] = useState(false);

  const [newSkillName, setNewSkillName] = useState("");
  const [newSkillCode, setNewSkillCode] = useState("");
  const [newSkillCat, setNewSkillCat] = useState("TECHNICAL");
  const [submittingSkill, setSubmittingSkill] = useState(false);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Handlers
  const handleCreateOrgUnit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgCode || !newOrgName) return;
    setSubmittingOrg(true);
    try {
      await api.post("/api/v3/workforce-planning/organization-units", {
        code: newOrgCode,
        name: newOrgName,
        parent_id: newOrgParent || null,
        active: true,
      });
      setNewOrgCode("");
      setNewOrgName("");
      setNewOrgParent("");
      setStatusMessage("Organization unit created successfully");
      mutateOrgUnits();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating organization unit");
    } finally {
      setSubmittingOrg(false);
    }
  };

  const handleCreatePosition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPosCode || !newPosTitle || !newPosOrg) return;
    setSubmittingPos(true);
    try {
      await api.post("/api/v3/workforce-planning/positions", {
        position_code: newPosCode,
        title: newPosTitle,
        organization_unit_id: newPosOrg,
        job_level: newPosLevel,
        headcount_capacity: Number(newPosCapacity),
        budgeted_cost: Number(newPosCost),
        currency: "INR",
        status: "OPEN",
      });
      setNewPosCode("");
      setNewPosTitle("");
      setNewPosOrg("");
      setNewPosCapacity(1.0);
      setNewPosCost(1200000);
      setStatusMessage("Position created successfully");
      mutatePositions();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating position");
    } finally {
      setSubmittingPos(false);
    }
  };

  const handleCreateHeadcountPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlanName) return;
    setSubmittingPlan(true);
    try {
      await api.post("/api/v3/workforce-planning/headcount-plans", {
        name: newPlanName,
        fiscal_year: newPlanYear,
        description: "Strategic workforce headcount allocation plan",
      });
      setNewPlanName("");
      setStatusMessage("Headcount plan created successfully");
      mutatePlans();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating headcount plan");
    } finally {
      setSubmittingPlan(false);
    }
  };

  const handleCreateSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSkillName || !newSkillCode) return;
    setSubmittingSkill(true);
    try {
      await api.post("/api/v3/workforce-planning/skills", {
        name: newSkillName,
        code: newSkillCode,
        category: newSkillCat,
      });
      setNewSkillName("");
      setNewSkillCode("");
      setStatusMessage("Skill registered successfully");
      mutateSkills();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating skill");
    } finally {
      setSubmittingSkill(false);
    }
  };

  const handleApprovePlan = async (planId: string) => {
    try {
      await api.post(`/api/v3/workforce-planning/headcount-plans/${planId}/approve`);
      setStatusMessage("Headcount plan approved");
      mutatePlans();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error approving plan");
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <span>🗺️</span> Strategic Workforce Planning & Org Design
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Enterprise headcount modeling, capacity governance, succession pipelines, and skills intelligence.
          </p>
        </div>
      </div>

      {/* Notifications */}
      {statusMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-lg text-sm flex justify-between items-center">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="text-emerald-600 hover:text-emerald-900 font-bold ml-4">
            ×
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 space-x-2 overflow-x-auto text-sm">
        {[
          { id: "overview", label: "Dashboard Overview", icon: "📊" },
          { id: "org-units", label: "Organization Units", icon: "🏛️" },
          { id: "positions", label: "Positions & Capacity", icon: "💼" },
          { id: "headcount", label: "Headcount & Demand", icon: "📈" },
          { id: "skills", label: "Skills Inventory", icon: "🎯" },
          { id: "succession", label: "Succession & Talent", icon: "🌟" },
          { id: "scenarios", label: "Workforce Scenarios", icon: "🧪" },
          { id: "mobility", label: "Internal Mobility", icon: "🔄" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 py-3 px-4 font-medium transition-colors border-b-2 whitespace-nowrap ${
              activeTab === tab.id
                ? "border-indigo-600 text-indigo-600 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Positions</p>
              <p className="text-2xl font-bold text-slate-900 mt-2">{dashboard?.total_positions ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Capacity: {dashboard?.total_headcount_capacity ?? 0}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Filled Headcount</p>
              <p className="text-2xl font-bold text-indigo-600 mt-2">{dashboard?.filled_headcount ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Fill Rate: {dashboard?.capacity_fill_rate_pct ?? 0}%</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Open Positions</p>
              <p className="text-2xl font-bold text-amber-600 mt-2">{dashboard?.open_positions ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Pending recruitment</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Critical Roles</p>
              <p className="text-2xl font-bold text-rose-600 mt-2">{dashboard?.critical_roles_count ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Succession Coverage: {dashboard?.succession_coverage_ratio ?? 0}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <span>⚖️</span> Workforce Demand & Supply Metrics
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Active Organization Units</span>
                  <span className="text-sm font-semibold text-slate-900">{orgUnits?.length ?? 0}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Cataloged Skills</span>
                  <span className="text-sm font-semibold text-slate-900">{dashboard?.total_skills_tracked ?? 0}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Identified Skill Gaps</span>
                  <span className="text-sm font-semibold text-rose-600">{dashboard?.skill_gap_count ?? 0}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-sm text-slate-600">Active Talent Pools</span>
                  <span className="text-sm font-semibold text-indigo-600">{dashboard?.active_talent_pools ?? 0}</span>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <span>⚡</span> Strategic Readiness & Governance
              </h3>
              <div className="space-y-3 text-sm text-slate-600">
                <p className="leading-relaxed">
                  Zeramai Strategic Workforce Planning connects organization hierarchies, position capacity boundaries,
                  hiring plans, and succession benches to ensure alignment with financial budgets.
                </p>
                <div className="mt-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <p className="font-medium text-slate-800">Governance Controls:</p>
                  <ul className="list-disc pl-5 mt-2 space-y-1 text-xs text-slate-600">
                    <li>Automated prevention of circular parent references in organizational trees</li>
                    <li>Headcount capacity enforcement preventing over-allocation</li>
                    <li>Primary assignment date overlap validation</li>
                    <li>Confidential salary and compensation budget masking for non-privileged roles</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Org Units */}
      {activeTab === "org-units" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Organization Hierarchy & Departments</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Code</th>
                    <th className="px-6 py-3">Unit Name</th>
                    <th className="px-6 py-3">Parent Unit</th>
                    <th className="px-6 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {orgUnits?.map((ou: any) => (
                    <tr key={ou.id} className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-mono font-medium text-slate-900">{ou.code}</td>
                      <td className="px-6 py-3 font-medium text-slate-900">{ou.name}</td>
                      <td className="px-6 py-3 text-slate-500">{ou.parent_name || "—"}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${ou.active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
                          {ou.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {(!orgUnits || orgUnits.length === 0) && (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-slate-400">
                        No organization units created yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-fit">
            <h3 className="font-semibold text-slate-900 mb-4">Create Organization Unit</h3>
            <form onSubmit={handleCreateOrgUnit} className="space-y-4 text-sm">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Unit Code *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ENG-DEV"
                  value={newOrgCode}
                  onChange={(e) => setNewOrgCode(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Unit Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Software Engineering"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Parent Unit</label>
                <select
                  value={newOrgParent}
                  onChange={(e) => setNewOrgParent(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">(None - Top Level)</option>
                  {orgUnits?.map((ou: any) => (
                    <option key={ou.id} value={ou.id}>
                      {ou.name} ({ou.code})
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={submittingOrg}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
              >
                {submittingOrg ? "Creating..." : "Create Org Unit"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab: Positions */}
      {activeTab === "positions" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
              <h3 className="font-semibold text-slate-900">Positions Directory</h3>
              <span className="text-xs text-slate-500">{positions?.length ?? 0} positions total</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Title</th>
                    <th className="px-4 py-3">Level</th>
                    <th className="px-4 py-3">Capacity</th>
                    <th className="px-4 py-3">Filled</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {positions?.map((pos: any) => (
                    <tr key={pos.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono font-medium text-slate-900">{pos.position_code}</td>
                      <td className="px-4 py-3 font-medium text-slate-900">{pos.title}</td>
                      <td className="px-4 py-3 text-xs">{pos.job_level}</td>
                      <td className="px-4 py-3 font-semibold text-slate-800">{pos.headcount_capacity}</td>
                      <td className="px-4 py-3 font-semibold text-indigo-600">{pos.filled_count}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                          pos.status === "OPEN" ? "bg-amber-100 text-amber-800" :
                          pos.status === "FILLED" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
                        }`}>
                          {pos.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {(!positions || positions.length === 0) && (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                        No positions registered yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-fit">
            <h3 className="font-semibold text-slate-900 mb-4">Create Position</h3>
            <form onSubmit={handleCreatePosition} className="space-y-4 text-sm">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Position Code *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. POS-ENG-SR"
                  value={newPosCode}
                  onChange={(e) => setNewPosCode(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Senior Software Engineer"
                  value={newPosTitle}
                  onChange={(e) => setNewPosTitle(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Department / Org Unit *</label>
                <select
                  required
                  value={newPosOrg}
                  onChange={(e) => setNewPosOrg(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Select Department</option>
                  {orgUnits?.map((ou: any) => (
                    <option key={ou.id} value={ou.id}>
                      {ou.name} ({ou.code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Job Level</label>
                  <select
                    value={newPosLevel}
                    onChange={(e) => setNewPosLevel(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="L1_ENTRY">L1 - Entry</option>
                    <option value="L2_INTERMEDIATE">L2 - Mid</option>
                    <option value="L3_SENIOR">L3 - Senior</option>
                    <option value="L4_LEAD">L4 - Lead / Staff</option>
                    <option value="L5_PRINCIPAL">L5 - Principal</option>
                    <option value="EXEC">Executive</option>
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Capacity (FTE)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    value={newPosCapacity}
                    onChange={(e) => setNewPosCapacity(parseFloat(e.target.value))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Budgeted Annual Cost (INR)</label>
                <input
                  type="number"
                  value={newPosCost}
                  onChange={(e) => setNewPosCost(parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={submittingPos}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
              >
                {submittingPos ? "Creating..." : "Create Position"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab: Headcount Plans */}
      {activeTab === "headcount" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
              <h3 className="font-semibold text-slate-900">Headcount & Demand Plans</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Plan Name</th>
                    <th className="px-6 py-3">Fiscal Year</th>
                    <th className="px-6 py-3">Planned Headcount</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {headcountPlans?.map((hp: any) => (
                    <tr key={hp.id} className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-900">{hp.name}</td>
                      <td className="px-6 py-3 font-mono">{hp.fiscal_year}</td>
                      <td className="px-6 py-3 font-semibold text-slate-800">{hp.total_planned_headcount}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                          hp.status === "APPROVED" ? "bg-emerald-100 text-emerald-800" :
                          hp.status === "SUBMITTED" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"
                        }`}>
                          {hp.status}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        {hp.status !== "APPROVED" && (
                          <button
                            onClick={() => handleApprovePlan(hp.id)}
                            className="text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-semibold px-2 py-1 rounded"
                          >
                            Approve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {(!headcountPlans || headcountPlans.length === 0) && (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                        No headcount plans created yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-fit">
            <h3 className="font-semibold text-slate-900 mb-4">Create Headcount Plan</h3>
            <form onSubmit={handleCreateHeadcountPlan} className="space-y-4 text-sm">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Plan Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. FY27 Strategic Growth Plan"
                  value={newPlanName}
                  onChange={(e) => setNewPlanName(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Fiscal Year *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2026-2027"
                  value={newPlanYear}
                  onChange={(e) => setNewPlanYear(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={submittingPlan}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
              >
                {submittingPlan ? "Creating..." : "Create Plan"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab: Skills */}
      {activeTab === "skills" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Enterprise Skills Catalog</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Code</th>
                    <th className="px-6 py-3">Skill Name</th>
                    <th className="px-6 py-3">Category</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {skills?.map((sk: any) => (
                    <tr key={sk.id} className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-mono font-medium text-slate-900">{sk.code}</td>
                      <td className="px-6 py-3 font-medium text-slate-900">{sk.name}</td>
                      <td className="px-6 py-3 text-xs">
                        <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                          {sk.category}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {(!skills || skills.length === 0) && (
                    <tr>
                      <td colSpan={3} className="px-6 py-8 text-center text-slate-400">
                        No skills cataloged yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-fit">
            <h3 className="font-semibold text-slate-900 mb-4">Add Skill</h3>
            <form onSubmit={handleCreateSkill} className="space-y-4 text-sm">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Skill Code *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. SKILL-REACT"
                  value={newSkillCode}
                  onChange={(e) => setNewSkillCode(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Skill Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. React & TypeScript"
                  value={newSkillName}
                  onChange={(e) => setNewSkillName(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Category</label>
                <select
                  value={newSkillCat}
                  onChange={(e) => setNewSkillCat(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="TECHNICAL">Technical</option>
                  <option value="DOMAIN">Domain</option>
                  <option value="LEADERSHIP">Leadership</option>
                  <option value="BEHAVIORAL">Behavioral</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={submittingSkill}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
              >
                {submittingSkill ? "Adding..." : "Add Skill"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab: Succession & Talent */}
      {activeTab === "succession" && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Critical Roles & Succession Pipeline</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Position</th>
                    <th className="px-6 py-3">Business Impact</th>
                    <th className="px-6 py-3">Vacancy Risk</th>
                    <th className="px-6 py-3">Current Incumbent</th>
                    <th className="px-6 py-3">Succession Coverage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {criticalRoles?.map((cr: any) => (
                    <tr key={cr.id} className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-900">{cr.position_title || cr.position_id}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded ${
                          cr.business_impact === "CRITICAL" ? "bg-rose-100 text-rose-800" : "bg-amber-100 text-amber-800"
                        }`}>
                          {cr.business_impact}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded ${
                          cr.vacancy_risk === "HIGH" ? "bg-rose-100 text-rose-800" : "bg-slate-100 text-slate-700"
                        }`}>
                          {cr.vacancy_risk}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-slate-800">{cr.current_incumbent || "Vacant"}</td>
                      <td className="px-6 py-3 font-semibold text-indigo-600">{cr.succession_coverage_count} candidate(s)</td>
                    </tr>
                  ))}
                  {(!criticalRoles || criticalRoles.length === 0) && (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                        No critical roles defined yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Talent Pools & Readiness</h3>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {talentPools?.map((tp: any) => (
                <div key={tp.id} className="p-4 rounded-lg border border-slate-200 bg-slate-50">
                  <p className="font-semibold text-slate-900">{tp.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{tp.description || "Talent bench pool"}</p>
                  <div className="mt-3 flex justify-between items-center text-xs">
                    <span className="font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                      {tp.member_count} Members
                    </span>
                    <span className="text-slate-400 uppercase">{tp.status}</span>
                  </div>
                </div>
              ))}
              {(!talentPools || talentPools.length === 0) && (
                <p className="text-sm text-slate-400 col-span-3">No talent pools created yet.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Scenarios */}
      {activeTab === "scenarios" && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Workforce Modeling Scenarios</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Scenario Name</th>
                    <th className="px-6 py-3">Type</th>
                    <th className="px-6 py-3">Headcount Delta</th>
                    <th className="px-6 py-3">Cost Delta (INR)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {scenarios?.map((sc: any) => (
                    <tr key={sc.id} className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-900">{sc.name}</td>
                      <td className="px-6 py-3 text-xs">
                        <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-mono">
                          {sc.scenario_type}
                        </span>
                      </td>
                      <td className="px-6 py-3 font-semibold text-slate-800">{sc.headcount_delta > 0 ? `+${sc.headcount_delta}` : sc.headcount_delta}</td>
                      <td className="px-6 py-3 font-mono text-slate-700">₹{sc.cost_delta?.toLocaleString() ?? 0}</td>
                    </tr>
                  ))}
                  {(!scenarios || scenarios.length === 0) && (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-slate-400">
                        No workforce scenarios modeled yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Strategic Hiring Plans</h3>
            </div>
            <div className="p-6">
              {hiringPlans?.map((hp: any) => (
                <div key={hp.id} className="p-4 rounded-lg border border-slate-200 mb-3 bg-slate-50">
                  <div className="flex justify-between items-center">
                    <p className="font-semibold text-slate-900">{hp.title}</p>
                    <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded">
                      {hp.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Period: {hp.target_period}</p>
                </div>
              ))}
              {(!hiringPlans || hiringPlans.length === 0) && (
                <p className="text-sm text-slate-400">No hiring plans active.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Mobility */}
      {activeTab === "mobility" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="font-semibold text-slate-900">Internal Mobility & Career Pathways</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Employee</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Current Role</th>
                  <th className="px-6 py-3">Target Role</th>
                  <th className="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {mobilityPlans?.map((mp: any) => (
                  <tr key={mp.id} className="hover:bg-slate-50">
                    <td className="px-6 py-3 font-medium text-slate-900">{mp.person_name || mp.person_id}</td>
                    <td className="px-6 py-3 text-xs">
                      <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-mono">
                        {mp.mobility_type}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-slate-700">{mp.current_position_title || "Current"}</td>
                    <td className="px-6 py-3 font-medium text-indigo-600">{mp.target_position_title || "Target"}</td>
                    <td className="px-6 py-3">
                      <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs font-semibold">
                        {mp.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {(!mobilityPlans || mobilityPlans.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                      No internal mobility plans configured yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
