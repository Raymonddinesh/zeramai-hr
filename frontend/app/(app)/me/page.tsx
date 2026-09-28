"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function EmployeeSelfServicePage() {
  const { data: essData, mutate, error } = useSWR("/v3/me", fetcher);
  const { data: myPolicies, mutate: mutateMyPolicies } = useSWR("/v3/hr-policies/my/applicable", fetcher);
  const { data: myDisciplinary, mutate: mutateMyDisciplinary } = useSWR("/v3/employee-relations/disciplinary", fetcher);

  const [activeTab, setActiveTab] = useState<
    "profile" | "attendance" | "leave" | "payroll" | "documents" | "performance" | "learning" | "assets" | "expenses" | "support" | "policies"
  >("profile");

  // Policy Acknowledgement Modal State
  const [selectedPolicyToAck, setSelectedPolicyToAck] = useState<any>(null);
  const [signatureText, setSignatureText] = useState("");
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [isSubmittingAck, setIsSubmittingAck] = useState(false);

  // Disciplinary Ack State
  const [selectedDiscToAck, setSelectedDiscToAck] = useState<any>(null);
  const [discSignature, setDiscSignature] = useState("");
  const [discComment, setDiscComment] = useState("");

  // Profile edit state
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [phone, setPhone] = useState("");
  const [preferredName, setPreferredName] = useState("");
  const [currentAddress, setCurrentAddress] = useState("");
  const [permanentAddress, setPermanentAddress] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");

  // Expense form state
  const [isAddingExpense, setIsAddingExpense] = useState(false);
  const [expenseCategory, setExpenseCategory] = useState("internet");
  const [expenseAmount, setExpenseAmount] = useState("");
  const [expenseDesc, setExpenseDesc] = useState("");
  const [expenseMerchant, setExpenseMerchant] = useState("");

  const handleStartEdit = () => {
    if (!essData?.profile) return;
    setPhone(essData.profile.phone || "");
    setPreferredName(essData.profile.preferred_name || "");
    setCurrentAddress(essData.profile.current_address || "");
    setPermanentAddress(essData.profile.permanent_address || "");
    setEmergencyContact(essData.profile.emergency_contact || "");
    setIsEditingProfile(true);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.patch("/v3/me/profile", {
        phone: phone || null,
        preferred_name: preferredName || null,
        current_address: currentAddress || null,
        permanent_address: permanentAddress || null,
        emergency_contact: emergencyContact || null,
      });
      alert("Personal profile updated successfully.");
      setIsEditingProfile(false);
      mutate();
    } catch {
      alert("Error updating profile.");
    }
  };

  const handleAddExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!expenseAmount || !expenseDesc) return;
    try {
      await api.post("/v3/me/expenses", {
        category: expenseCategory,
        amount: parseFloat(expenseAmount),
        currency: "INR",
        description: expenseDesc,
        merchant: expenseMerchant || null,
      });
      alert("Expense claim submitted.");
      setExpenseAmount("");
      setExpenseDesc("");
      setExpenseMerchant("");
      setIsAddingExpense(false);
      mutate();
    } catch {
      alert("Error submitting expense claim.");
    }
  };

  if (!essData && !error) {
    return <div className="p-8 text-sm text-gray-500">Loading your employee portal...</div>;
  }

  const profile = essData?.profile;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl font-bold text-gray-900">{profile?.full_name}</span>
            <span className="bg-indigo-100 text-indigo-800 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
              {profile?.status || "Active"}
            </span>
          </div>
          <p className="text-xs text-gray-500">
            {profile?.designation || "Employee"} • {profile?.department || "Department"} • {profile?.email}
          </p>
          {profile?.reporting_manager_name && (
            <p className="text-[11px] text-gray-400 mt-1">
              Reporting Manager: <strong className="text-gray-700">{profile.reporting_manager_name}</strong>
            </p>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleStartEdit}
            className="bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-semibold px-3 py-1.5 rounded-lg border border-indigo-200 text-xs transition"
          >
            ✏️ Update Contact Info
          </button>
        </div>
      </div>

      {/* Offboarding Alert if Active */}
      {essData?.offboarding && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 flex justify-between items-center text-xs">
          <div>
            <span className="font-bold text-purple-900">Active Exit Case ({essData.offboarding.ticket_number})</span>
            <p className="text-purple-700 mt-0.5">
              Status: <span className="uppercase font-semibold">{essData.offboarding.status}</span> • Last Working Day:{" "}
              {essData.offboarding.approved_last_working_day || essData.offboarding.proposed_last_working_day}
            </p>
          </div>
          <a
            href="/offboarding"
            className="bg-purple-600 text-white font-medium px-3 py-1.5 rounded-lg text-xs hover:bg-purple-700 transition"
          >
            Go to Exit Portal →
          </a>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        {[
          { id: "profile", label: "👤 Profile" },
          { id: "attendance", label: "📅 Attendance" },
          { id: "leave", label: "🏖️ Leave" },
          { id: "payroll", label: "💵 Compensation & Payroll" },
          { id: "documents", label: "📄 Documents" },

          { id: "performance", label: "🎯 OKRs" },
          { id: "learning", label: "🎓 LMS" },
          { id: "assets", label: "💻 Assets" },
          { id: "expenses", label: "💰 Expenses" },
          { id: "support", label: "🎫 HR Requests" },
          { id: "policies", label: "📜 Policies & Conduct" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition ${
              activeTab === tab.id
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: Profile */}
      {activeTab === "profile" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            {/* Personal & Contact */}
            <div className="space-y-3">
              <h4 className="font-bold text-gray-900 border-b pb-1.5">Personal & Contact Information</h4>
              <div className="space-y-2 text-gray-700">
                <p><span className="text-gray-400 w-32 inline-block">Full Name:</span> {profile?.full_name}</p>
                <p><span className="text-gray-400 w-32 inline-block">Preferred Name:</span> {profile?.preferred_name || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Work Email:</span> {profile?.email}</p>
                <p><span className="text-gray-400 w-32 inline-block">Mobile Phone:</span> {profile?.phone || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Current Address:</span> {profile?.current_address || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Permanent Address:</span> {profile?.permanent_address || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Emergency Contact:</span> {profile?.emergency_contact || "—"}</p>
              </div>
            </div>

            {/* Employment Record */}
            <div className="space-y-3">
              <h4 className="font-bold text-gray-900 border-b pb-1.5">Employment Master Record</h4>
              <div className="space-y-2 text-gray-700">
                <p><span className="text-gray-400 w-32 inline-block">Designation:</span> {profile?.designation || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Department:</span> {profile?.department || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Employment Type:</span> <span className="capitalize">{profile?.engagement_type?.replace("_", " ") || "—"}</span></p>
                <p><span className="text-gray-400 w-32 inline-block">Joining Date:</span> {profile?.start_date || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Reporting Manager:</span> {profile?.reporting_manager_name || "—"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Work Location:</span> {profile?.work_location || "Headquarters"}</p>
                <p><span className="text-gray-400 w-32 inline-block">Account Status:</span> <span className="capitalize font-semibold text-emerald-700">{profile?.status}</span></p>
              </div>
            </div>
          </div>

          {/* Edit Modal / Form */}
          {isEditingProfile && (
            <div className="p-4 bg-slate-50 border rounded-xl space-y-4 text-xs mt-4">
              <h4 className="font-bold text-gray-900">Update Self-Service Personal Fields</h4>
              <p className="text-[11px] text-gray-500">
                You can update your personal contact info and address. HR-controlled fields (Designation, Email, Department) cannot be modified here.
              </p>
              <form onSubmit={handleSaveProfile} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Preferred Name</label>
                  <input
                    type="text"
                    value={preferredName}
                    onChange={(e) => setPreferredName(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Mobile Phone</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Current Residential Address</label>
                  <input
                    type="text"
                    value={currentAddress}
                    onChange={(e) => setCurrentAddress(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Permanent Address</label>
                  <input
                    type="text"
                    value={permanentAddress}
                    onChange={(e) => setPermanentAddress(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-gray-700 font-medium mb-1">Emergency Contact Details</label>
                  <input
                    type="text"
                    placeholder="Name, relationship, contact number"
                    value={emergencyContact}
                    onChange={(e) => setEmergencyContact(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div className="md:col-span-2 flex gap-2">
                  <button
                    type="submit"
                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-1.5 rounded-lg text-xs transition"
                  >
                    Save Changes
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditingProfile(false)}
                    className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium px-4 py-1.5 rounded-lg text-xs transition"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Tab: Attendance */}
      {activeTab === "attendance" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-gray-900 text-sm">Recent Attendance Records</h4>
            <a href="/attendance" className="text-indigo-600 hover:underline text-xs font-semibold">
              Full Attendance View →
            </a>
          </div>
          <div className="overflow-x-auto text-xs">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b text-gray-400 uppercase text-[10px]">
                  <th className="py-2">Date</th>
                  <th className="py-2">Status</th>
                  <th className="py-2">Check In</th>
                  <th className="py-2">Check Out</th>
                  <th className="py-2">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(essData?.attendance || []).map((a: any) => (
                  <tr key={a.id} className="text-gray-700">
                    <td className="py-2.5 font-medium">{a.date}</td>
                    <td className="py-2.5">
                      <span className="capitalize font-semibold text-emerald-700">{a.status}</span>
                    </td>
                    <td className="py-2.5">{a.check_in ? new Date(a.check_in).toLocaleTimeString() : "—"}</td>
                    <td className="py-2.5">{a.check_out ? new Date(a.check_out).toLocaleTimeString() : "—"}</td>
                    <td className="py-2.5 text-gray-500">{a.notes || "—"}</td>
                  </tr>
                ))}
                {(!essData?.attendance || essData.attendance.length === 0) && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-gray-400">No recent attendance records.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Leave */}
      {activeTab === "leave" && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {(essData?.leave?.balances || []).map((b: any, idx: number) => (
              <div key={idx} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm text-xs">
                <span className="text-gray-400 block text-[10px] uppercase">{b.policy_name}</span>
                <p className="text-2xl font-bold text-indigo-700 mt-1">{b.balance} Days</p>
                <span className="text-[11px] text-gray-500 capitalize">{b.leave_type} Balance</span>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <h4 className="font-bold text-gray-900 text-sm">Recent Leave Requests</h4>
              <a href="/leave" className="text-indigo-600 hover:underline text-xs font-semibold">
                Apply for Leave →
              </a>
            </div>
            <div className="space-y-2">
              {(essData?.leave?.recent_requests || []).map((r: any) => (
                <div key={r.id} className="p-3 border rounded-lg bg-gray-50 flex justify-between items-center">
                  <div>
                    <span className="font-semibold text-gray-800 capitalize">{r.leave_type} Leave</span>
                    <p className="text-[11px] text-gray-500">{r.start_date} to {r.end_date} • {r.reason || "No reason given"}</p>
                  </div>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                    {r.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Payroll & Compensation */}
      {activeTab === "payroll" && (
        <div className="space-y-6 text-xs">
          {/* Approved Compensation Breakdown */}
          {essData?.compensation && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
              <div className="flex justify-between items-center border-b pb-3">
                <div>
                  <h4 className="font-bold text-gray-900 text-sm">Approved Compensation Structure</h4>
                  <p className="text-gray-500 text-[11px] mt-0.5">
                    Effective from: {essData.compensation.effective_from} • Currency: {essData.compensation.currency}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-gray-500 block">Total Annual CTC</span>
                  <span className="text-lg font-bold text-gray-900">
                    ₹{essData.compensation.ctc_annual?.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="text-gray-500 block text-[10px] uppercase font-semibold">Monthly Gross</span>
                  <p className="text-base font-bold text-indigo-700 mt-0.5">
                    ₹{essData.compensation.ctc_monthly?.toLocaleString()}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="text-gray-500 block text-[10px] uppercase font-semibold">Annual CTC</span>
                  <p className="text-base font-bold text-gray-900 mt-0.5">
                    ₹{essData.compensation.ctc_annual?.toLocaleString()}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="text-gray-500 block text-[10px] uppercase font-semibold">Status</span>
                  <span className="inline-block mt-1 bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded text-[10px] uppercase">
                    Active & Approved
                  </span>
                </div>
              </div>

              <div>
                <h5 className="font-semibold text-gray-800 mb-2">Salary Component Breakdown</h5>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {(essData.compensation.components || []).map((c: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center p-2.5 bg-gray-50 rounded border border-gray-100">
                      <div>
                        <span className="font-semibold text-gray-800">{c.name || c.code}</span>
                        <span className="text-[10px] text-gray-400 block uppercase font-mono">{c.code}</span>
                      </div>
                      <span className="font-bold text-gray-900">₹{c.amount?.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Enrolled Benefits */}
          {(essData?.benefits || []).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-3">
              <h4 className="font-bold text-gray-900 text-sm">Enrolled Corporate Benefits</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {essData.benefits.map((b: any) => (
                  <div key={b.id} className="p-3.5 bg-gray-50 rounded-lg border border-gray-200 space-y-1">
                    <div className="flex justify-between items-start">
                      <span className="font-bold text-gray-900">{b.plan_name}</span>
                      <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                        {b.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-500">{b.provider || "Company Sponsored"} • Coverage: {b.coverage_tier?.replace("_", " ")}</p>
                    <div className="flex justify-between text-[11px] text-gray-600 border-t pt-1.5 mt-2">
                      <span>Employer: ₹{b.employer_contribution}</span>
                      <span>Deduction: ₹{b.employee_contribution}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Monthly Payslips */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
            <h4 className="font-bold text-gray-900 text-sm">Monthly Payslips</h4>
            <p className="text-gray-500">
              View your gross salary, statutory deductions, and net deposited compensation.
            </p>
            <div className="space-y-2.5">
              {(essData?.payslips || []).map((p: any) => (
                <div key={p.id} className="p-3.5 border rounded-lg bg-gray-50 flex justify-between items-center">
                  <div>
                    <span className="font-bold text-gray-800">Payslip for {p.month}</span>
                    <p className="text-[11px] text-gray-500">Gross: ₹{p.gross_pay?.toLocaleString()} • Deductions: ₹{p.total_deductions?.toLocaleString()}</p>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-emerald-700 text-sm">₹{p.net_pay?.toLocaleString()}</span>
                    <span className="block text-[10px] text-gray-400">Net Disbursed</span>
                  </div>
                </div>
              ))}
              {(!essData?.payslips || essData.payslips.length === 0) && (
                <p className="text-gray-400 text-center py-6">No payslips generated for this period.</p>
              )}
            </div>
          </div>
        </div>
      )}


      {/* Tab: Documents */}
      {activeTab === "documents" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4 text-xs">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-gray-900 text-sm">Employee Documents</h4>
            <a href="/documents" className="text-indigo-600 hover:underline text-xs font-semibold">
              Upload Document →
            </a>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(essData?.documents || []).map((d: any) => (
              <div key={d.id} className="p-3.5 border rounded-lg bg-gray-50 flex justify-between items-center">
                <div>
                  <span className="font-semibold text-gray-800 uppercase text-[10px] tracking-wider text-indigo-700">{d.document_type}</span>
                  <h5 className="font-medium text-gray-900 text-xs mt-0.5">{d.file_name}</h5>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 capitalize">
                  {d.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Performance */}
      {activeTab === "performance" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4 text-xs">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-gray-900 text-sm">My OKRs & Objectives</h4>
            {essData?.performance?.latest_review_rating && (
              <span className="bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-1 rounded text-[11px] font-semibold">
                Latest Review: {essData.performance.latest_review_rating}
              </span>
            )}
          </div>
          <div className="space-y-3">
            {(essData?.performance?.objectives || []).map((o: any) => (
              <div key={o.id} className="p-3.5 border rounded-lg bg-gray-50 space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-gray-800 text-xs">{o.title}</span>
                  <span className="font-bold text-indigo-700">{o.progress_percentage}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div className="bg-indigo-600 h-1.5 rounded-full" style={{ width: `${o.progress_percentage}%` }}></div>
                </div>
              </div>
            ))}
            {(!essData?.performance?.objectives || essData.performance.objectives.length === 0) && (
              <p className="text-gray-400 text-center py-6">No OKR objectives assigned yet.</p>
            )}
          </div>
        </div>
      )}

      {/* Tab: Learning */}
      {activeTab === "learning" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4 text-xs">
          <h4 className="font-bold text-gray-900 text-sm">Learning & Development (LMS)</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-center">
              <span className="text-2xl font-bold text-blue-700">{essData?.learning?.enrolled_courses_count || 0}</span>
              <p className="text-gray-600 text-[11px] mt-1">Enrolled Courses</p>
            </div>
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center">
              <span className="text-2xl font-bold text-emerald-700">{essData?.learning?.completed_courses_count || 0}</span>
              <p className="text-gray-600 text-[11px] mt-1">Completed Modules</p>
            </div>
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-center">
              <span className="text-2xl font-bold text-amber-700">{essData?.learning?.certificates_count || 0}</span>
              <p className="text-gray-600 text-[11px] mt-1">Earned Certificates</p>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Assets */}
      {activeTab === "assets" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4 text-xs">
          <h4 className="font-bold text-gray-900 text-sm">Assigned Company Assets & Hardware</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(essData?.assets || []).map((a: any) => (
              <div key={a.id} className="p-3.5 border rounded-lg bg-gray-50 flex justify-between items-center">
                <div>
                  <span className="text-[10px] uppercase font-bold text-gray-500">{a.asset_type}</span>
                  <h5 className="font-bold text-gray-800 text-xs mt-0.5">{a.asset_name}</h5>
                  {a.serial_number && <p className="text-[10px] text-gray-400 font-mono mt-0.5">S/N: {a.serial_number}</p>}
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 capitalize">
                  {a.return_status}
                </span>
              </div>
            ))}
            {(!essData?.assets || essData.assets.length === 0) && (
              <p className="text-gray-400 text-center py-6 col-span-2">No physical assets assigned to your account.</p>
            )}
          </div>
        </div>
      )}

      {/* Tab: Expenses */}
      {activeTab === "expenses" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4 text-xs">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-gray-900 text-sm">Expense Claims & Reimbursements</h4>
            <button
              onClick={() => setIsAddingExpense(!isAddingExpense)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-3 py-1.5 rounded-lg text-xs transition"
            >
              ➕ New Claim
            </button>
          </div>

          {isAddingExpense && (
            <form onSubmit={handleAddExpense} className="p-4 bg-slate-50 border rounded-xl space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Category</label>
                  <select
                    value={expenseCategory}
                    onChange={(e) => setExpenseCategory(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  >
                    <option value="internet">Broadband / Internet</option>
                    <option value="travel">Travel & Transport</option>
                    <option value="meals">Client Meals</option>
                    <option value="equipment">Office Supplies</option>
                    <option value="learning">Certifications / Books</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Amount (INR)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="e.g. 1500"
                    value={expenseAmount}
                    onChange={(e) => setExpenseAmount(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-gray-700 font-medium mb-1">Merchant / Vendor</label>
                  <input
                    type="text"
                    placeholder="e.g. Airtel / Uber"
                    value={expenseMerchant}
                    onChange={(e) => setExpenseMerchant(e.target.value)}
                    className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
              </div>
              <div>
                <label className="block text-gray-700 font-medium mb-1">Description</label>
                <input
                  type="text"
                  required
                  placeholder="Justification or business purpose..."
                  value={expenseDesc}
                  onChange={(e) => setExpenseDesc(e.target.value)}
                  className="w-full border rounded-lg px-2.5 py-1.5 text-xs"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-1.5 rounded-lg text-xs transition"
                >
                  Submit Claim
                </button>
                <button
                  type="button"
                  onClick={() => setIsAddingExpense(false)}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium px-4 py-1.5 rounded-lg text-xs transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="space-y-2">
            {(essData?.expenses || []).map((e: any) => (
              <div key={e.id} className="p-3 border rounded-lg bg-gray-50 flex justify-between items-center">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-indigo-700 font-bold">{e.ticket_number}</span>
                    <span className="font-medium text-gray-800 capitalize">{e.category}</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">{e.description} • {e.merchant || "Vendor"}</p>
                </div>
                <div className="text-right">
                  <span className="font-bold text-gray-900 text-sm">₹{e.amount?.toLocaleString()}</span>
                  <span className={`block text-[10px] font-bold uppercase ${e.status === "approved" ? "text-emerald-700" : "text-amber-700"}`}>
                    {e.status}
                  </span>
                </div>
              </div>
            ))}
            {(!essData?.expenses || essData.expenses.length === 0) && (
              <p className="text-gray-400 text-center py-6">No expense claims filed yet.</p>
            )}
          </div>
        </div>
      )}

      {/* Tab: Support / HR Requests */}
      {activeTab === "support" && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4 text-xs">
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-gray-900 text-sm">My HR Service Desk Requests</h4>
            <a href="/hr-requests" className="text-indigo-600 hover:underline text-xs font-semibold">
              Open Support Portal →
            </a>
          </div>
          <div className="space-y-2">
            {(essData?.hr_requests || []).map((hr: any) => (
              <div key={hr.id} className="p-3 border rounded-lg bg-gray-50 flex justify-between items-center">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-indigo-700">{hr.ticket_number}</span>
                    <span className="font-semibold text-gray-800">{hr.subject}</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5 capitalize">{hr.category?.replace("_", " ")}</p>
                </div>
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                  {hr.status?.replace("_", " ")}
                </span>
              </div>
            ))}
            {(!essData?.hr_requests || essData.hr_requests.length === 0) && (
              <p className="text-gray-400 text-center py-6">No support tickets logged.</p>
            )}
          </div>
        </div>
      )}

      {/* Tab: Policies & Conduct */}
      {activeTab === "policies" && (
        <div className="space-y-6 text-xs">
          {/* Handbooks & Policies Section */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
            <div>
              <h4 className="font-bold text-gray-900 text-sm">Company Policies & Handbooks</h4>
              <p className="text-gray-500 text-[11px] mt-0.5">
                Review and electronically acknowledge company policies applicable to your employment role and department.
              </p>
            </div>

            <div className="divide-y divide-gray-200 border rounded-xl overflow-hidden">
              {(myPolicies || []).length === 0 ? (
                <div className="p-8 text-center text-gray-400">No applicable policies published for your profile.</div>
              ) : (
                myPolicies?.map((pol: any) => (
                  <div key={pol.id} className="p-4 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-gray-50/60 transition">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900 text-sm">{pol.title}</span>
                        <span className="font-mono text-[10px] px-1.5 py-0.5 bg-gray-100 rounded text-gray-600">
                          v{pol.version}
                        </span>
                        {pol.is_mandatory && (
                          <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-amber-100 text-amber-800">
                            Mandatory
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-gray-500 mt-1 flex items-center gap-2">
                        <span className="font-mono">{pol.policy_code}</span>
                        <span>•</span>
                        <span className="capitalize">{pol.category?.replace(/_/g, " ")}</span>
                        <span>•</span>
                        <span>Effective: {pol.effective_date}</span>
                      </div>
                      {pol.description && (
                        <p className="text-gray-600 text-xs mt-1 max-w-xl">{pol.description}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      {pol.has_acknowledged ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full font-medium text-xs border border-emerald-200">
                          ✓ Acknowledged
                        </span>
                      ) : (
                        <button
                          onClick={() => {
                            setSelectedPolicyToAck(pol);
                            setSignatureText(essData?.profile?.full_name || "");
                            setConfirmChecked(false);
                          }}
                          className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-xs shadow-sm transition"
                        >
                          Review & Sign
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Formal Disciplinary & Conduct Notices Section */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
            <div>
              <h4 className="font-bold text-gray-900 text-sm">Formal Disciplinary & Conduct Notices</h4>
              <p className="text-gray-500 text-[11px] mt-0.5">
                Official notices and performance improvement records issued to your profile.
              </p>
            </div>

            <div className="space-y-3">
              {(myDisciplinary || []).length === 0 ? (
                <div className="p-6 text-center text-gray-400 bg-gray-50 rounded-xl border border-dashed">
                  No disciplinary actions or performance warnings on your employee record.
                </div>
              ) : (
                myDisciplinary?.map((d: any) => (
                  <div key={d.id} className="p-4 rounded-xl border border-purple-200 bg-purple-50/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold uppercase text-purple-900 text-xs px-2 py-0.5 rounded bg-purple-100">
                          {d.action_type?.replace(/_/g, " ")}
                        </span>
                        <span className="text-gray-500 text-xs">Issued on {d.issued_date}</span>
                      </div>
                      <p className="font-medium text-gray-800 text-xs mt-1.5">{d.reason}</p>
                      {d.action_plan && (
                        <p className="text-gray-600 text-[11px] mt-1 bg-white p-2 rounded border border-purple-100">
                          <strong>Action Plan:</strong> {d.action_plan}
                        </p>
                      )}
                    </div>

                    <div>
                      {d.employee_acknowledged ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 font-medium text-xs">
                          ✓ Acknowledged
                        </span>
                      ) : (
                        <button
                          onClick={() => {
                            setSelectedDiscToAck(d);
                            setDiscSignature(essData?.profile?.full_name || "");
                            setDiscComment("");
                          }}
                          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-medium transition"
                        >
                          Acknowledge Notice
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Review & Acknowledge Policy Modal */}
      {selectedPolicyToAck && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-start justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-gray-900">{selectedPolicyToAck.title}</h3>
                <p className="text-xs text-gray-500 font-mono">{selectedPolicyToAck.policy_code} • Version {selectedPolicyToAck.version}</p>
              </div>
              <button onClick={() => setSelectedPolicyToAck(null)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
                &times;
              </button>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Document Content</h4>
              <div className="p-4 bg-gray-50 border rounded-xl max-h-60 overflow-y-auto text-xs text-gray-800 whitespace-pre-wrap leading-relaxed">
                {selectedPolicyToAck.content}
              </div>
            </div>

            <div className="space-y-3 pt-3 border-t">
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={confirmChecked}
                  onChange={(e) => setConfirmChecked(e.target.checked)}
                  className="w-4 h-4 text-indigo-600 rounded mt-0.5"
                />
                <span className="text-xs text-gray-700">
                  I confirm that I have carefully read, understood, and agreed to comply with all guidelines, stipulations, and standards outlined in this policy document.
                </span>
              </label>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Electronic Signature (Full Legal Name) *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Jane Doe"
                  value={signatureText}
                  onChange={(e) => setSignatureText(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 text-xs font-medium"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedPolicyToAck(null)}
                  className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  disabled={!confirmChecked || !signatureText.trim() || isSubmittingAck}
                  onClick={async () => {
                    setIsSubmittingAck(true);
                    try {
                      await api.post(`/v3/hr-policies/${selectedPolicyToAck.id}/acknowledge`, {
                        signature_text: signatureText,
                        confirmation_checked: confirmChecked,
                      });
                      alert("Policy electronically acknowledged successfully.");
                      setSelectedPolicyToAck(null);
                      mutateMyPolicies();
                    } catch (err: any) {
                      alert(err?.response?.data?.detail || "Failed to acknowledge policy");
                    } finally {
                      setIsSubmittingAck(false);
                    }
                  }}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-medium shadow-sm transition"
                >
                  {isSubmittingAck ? "Submitting..." : "Sign & Acknowledge"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Acknowledge Disciplinary Action Modal */}
      {selectedDiscToAck && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Acknowledge Disciplinary Notice</h3>
                <p className="text-xs text-gray-500 capitalize">{selectedDiscToAck.action_type?.replace(/_/g, " ")}</p>
              </div>
              <button onClick={() => setSelectedDiscToAck(null)} className="text-gray-400 hover:text-gray-600 text-xl font-bold">
                &times;
              </button>
            </div>

            <div className="text-xs text-gray-700 space-y-2 bg-gray-50 p-3 rounded-lg">
              <p><strong>Reason:</strong> {selectedDiscToAck.reason}</p>
              {selectedDiscToAck.action_plan && (
                <p><strong>Action Plan:</strong> {selectedDiscToAck.action_plan}</p>
              )}
            </div>

            <div className="space-y-3 pt-2 text-xs">
              <div>
                <label className="block text-gray-700 font-medium mb-1">Employee Comment (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Any remarks or acknowledgement statement..."
                  value={discComment}
                  onChange={(e) => setDiscComment(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 text-xs"
                />
              </div>

              <div>
                <label className="block text-gray-700 font-medium mb-1">Electronic Signature (Full Name) *</label>
                <input
                  type="text"
                  required
                  value={discSignature}
                  onChange={(e) => setDiscSignature(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setSelectedDiscToAck(null)}
                  className="px-4 py-2 border text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  disabled={!discSignature.trim() || isSubmittingAck}
                  onClick={async () => {
                    setIsSubmittingAck(true);
                    try {
                      await api.post(`/v3/employee-relations/disciplinary/${selectedDiscToAck.id}/acknowledge`, {
                        signature_text: discSignature,
                        employee_comment: discComment || undefined,
                      });
                      alert("Notice acknowledged.");
                      setSelectedDiscToAck(null);
                      mutateMyDisciplinary();
                    } catch (err: any) {
                      alert(err?.response?.data?.detail || "Failed to acknowledge notice");
                    } finally {
                      setIsSubmittingAck(false);
                    }
                  }}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg text-xs font-medium shadow-sm transition"
                >
                  {isSubmittingAck ? "Submitting..." : "Confirm Acknowledgement"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
