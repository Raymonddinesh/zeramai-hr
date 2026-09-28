"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function LearningPage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "catalog" | "my-learning" | "certifications" | "career" | "idp" | "mentoring" | "admin"
  >("overview");

  // Data fetching
  const { data: dashboard, mutate: mutateDashboard } = useSWR("/api/v3/learning/dashboard", fetcher);
  const { data: courses, mutate: mutateCourses } = useSWR("/api/v3/learning/courses", fetcher);
  const { data: paths, mutate: mutatePaths } = useSWR("/api/v3/learning/paths", fetcher);
  const { data: enrollments, mutate: mutateEnrollments } = useSWR("/api/v3/learning/enrollments", fetcher);
  const { data: certifications, mutate: mutateCerts } = useSWR("/api/v3/learning/certifications", fetcher);
  const { data: empCerts, mutate: mutateEmpCerts } = useSWR("/api/v3/learning/employee-certifications", fetcher);
  const { data: frameworks, mutate: mutateFrameworks } = useSWR("/api/v3/learning/career-frameworks", fetcher);
  const { data: opportunities, mutate: mutateOpportunities } = useSWR("/api/v3/learning/career-opportunities", fetcher);
  const { data: devPlans, mutate: mutateDevPlans } = useSWR("/api/v3/learning/development-plans", fetcher);
  const { data: mentoringProgs, mutate: mutateMentoring } = useSWR("/api/v3/learning/mentoring/programs", fetcher);
  const { data: mentoringRels, mutate: mutateMentoringRels } = useSWR("/api/v3/learning/mentoring/relationships", fetcher);
  const { data: analytics } = useSWR("/api/v3/learning/analytics", fetcher);

  // Form states
  const [newCourseCode, setNewCourseCode] = useState("");
  const [newCourseTitle, setNewCourseTitle] = useState("");
  const [newCourseCat, setNewCourseCat] = useState("TECHNICAL");
  const [newCourseType, setNewCourseType] = useState("COURSE");
  const [newCourseDiff, setNewCourseDiff] = useState("INTERMEDIATE");
  const [newCourseDuration, setNewCourseDuration] = useState(60);
  const [submittingCourse, setSubmittingCourse] = useState(false);

  const [newCertName, setNewCertName] = useState("");
  const [newCertBody, setNewCertBody] = useState("");
  const [submittingCert, setSubmittingCert] = useState(false);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Handlers
  const handleEnroll = async (courseId: string) => {
    try {
      await api.post("/api/v3/learning/enrollments", {
        person_id: "self",
        course_id: courseId,
        enrollment_type: "SELF",
      });
      setStatusMessage("Enrolled in course successfully!");
      mutateEnrollments();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Enrollment failed");
    }
  };

  const handleUpdateProgress = async (enrollmentId: string, currentPct: number) => {
    const nextPct = Math.min(100, currentPct + 25);
    try {
      await api.post(`/api/v3/learning/enrollments/${enrollmentId}/progress`, {
        progress_percentage: nextPct,
        time_spent_minutes: 30,
      });
      setStatusMessage(`Progress updated to ${nextPct}%`);
      mutateEnrollments();
      mutateDashboard();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error updating progress");
    }
  };

  const handleApplyOpportunity = async (oppId: string) => {
    try {
      await api.post("/api/v3/learning/career-applications", {
        opportunity_id: oppId,
      });
      setStatusMessage("Application submitted successfully!");
      mutateOpportunities();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Application failed");
    }
  };

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCourseCode || !newCourseTitle) return;
    setSubmittingCourse(true);
    try {
      await api.post("/api/v3/learning/courses", {
        course_code: newCourseCode,
        title: newCourseTitle,
        category: newCourseCat,
        learning_type: newCourseType,
        difficulty: newCourseDiff,
        duration_minutes: Number(newCourseDuration),
        status: "PUBLISHED",
      });
      setNewCourseCode("");
      setNewCourseTitle("");
      setStatusMessage("Course created and published successfully");
      mutateCourses();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating course");
    } finally {
      setSubmittingCourse(false);
    }
  };

  const handleCreateCert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCertName || !newCertBody) return;
    setSubmittingCert(true);
    try {
      await api.post("/api/v3/learning/certifications", {
        name: newCertName,
        issuing_body: newCertBody,
        validity_months: 24,
      });
      setNewCertName("");
      setNewCertBody("");
      setStatusMessage("Certification cataloged successfully");
      mutateCerts();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error creating certification");
    } finally {
      setSubmittingCert(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <span>🎓</span> Enterprise Learning, Skills & Career Development
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Modular course catalogs, learning paths, credential tracking, career frameworks, and structured mentoring.
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
          { id: "overview", label: "My Learning Hub", icon: "🏠" },
          { id: "catalog", label: "Course Catalog", icon: "📚" },
          { id: "my-learning", label: "Active Enrollments", icon: "⚡" },
          { id: "certifications", label: "Certifications", icon: "🎖️" },
          { id: "career", label: "Career & Internal Mobility", icon: "🚀" },
          { id: "idp", label: "Individual Development", icon: "🎯" },
          { id: "mentoring", label: "Mentoring Programs", icon: "🤝" },
          { id: "admin", label: "L&D Administration", icon: "⚙️" },
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
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">In-Progress Courses</p>
              <p className="text-2xl font-bold text-indigo-600 mt-2">{dashboard?.in_progress_courses_count ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Active learning modules</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completed Courses</p>
              <p className="text-2xl font-bold text-emerald-600 mt-2">{dashboard?.completed_courses_count ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Verified achievements</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Credentials</p>
              <p className="text-2xl font-bold text-amber-600 mt-2">{dashboard?.active_certifications_count ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Expiring in 30d: {dashboard?.expiring_certifications_count ?? 0}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Mentoring</p>
              <p className="text-2xl font-bold text-rose-600 mt-2">{dashboard?.active_mentoring_count ?? 0}</p>
              <p className="text-xs text-slate-400 mt-1">Pair relationships</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <span>📖</span> Recent Course Enrollments
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Course Title</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Progress</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {enrollments?.slice(0, 5).map((e: any) => (
                    <tr key={e.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-medium text-slate-900">{e.course_title || e.course_id}</td>
                      <td className="px-4 py-3 text-xs">{e.enrollment_type}</td>
                      <td className="px-4 py-3">
                        <div className="w-32 bg-slate-200 rounded-full h-2">
                          <div
                            className="bg-indigo-600 h-2 rounded-full"
                            style={{ width: `${e.progress_percentage}%` }}
                          />
                        </div>
                        <span className="text-[11px] text-slate-400">{e.progress_percentage}%</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                          e.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" :
                          e.status === "IN_PROGRESS" ? "bg-indigo-100 text-indigo-800" : "bg-slate-100 text-slate-600"
                        }`}>
                          {e.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {(!enrollments || enrollments.length === 0) && (
                    <tr>
                      <td colSpan={4} className="px-4 py-6 text-center text-slate-400">
                        No active course enrollments. Browse the catalog to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Catalog */}
      {activeTab === "catalog" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses?.map((c: any) => (
              <div key={c.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start">
                    <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-mono font-medium">
                      {c.course_code}
                    </span>
                    <span className="text-xs text-slate-500 font-medium">⏳ {c.duration_minutes}m</span>
                  </div>
                  <h4 className="font-bold text-slate-900 text-base mt-2">{c.title}</h4>
                  <p className="text-xs text-slate-600 mt-1 line-clamp-3">
                    {c.description || "Comprehensive enterprise training module covering key architectural standards."}
                  </p>
                </div>
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-medium bg-slate-100 px-2 py-0.5 rounded">
                    {c.difficulty}
                  </span>
                  <button
                    onClick={() => handleEnroll(c.id)}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs py-1.5 px-3 rounded-lg font-medium shadow-sm transition"
                  >
                    + Enroll
                  </button>
                </div>
              </div>
            ))}
            {(!courses || courses.length === 0) && (
              <p className="text-sm text-slate-400 col-span-3 text-center py-10">No published courses available.</p>
            )}
          </div>
        </div>
      )}

      {/* Tab: Active Enrollments */}
      {activeTab === "my-learning" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="font-semibold text-slate-900">Active Course Progress & Completion</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Course</th>
                  <th className="px-6 py-3">Enrolled At</th>
                  <th className="px-6 py-3">Progress</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {enrollments?.map((e: any) => (
                  <tr key={e.id} className="hover:bg-slate-50">
                    <td className="px-6 py-3 font-medium text-slate-900">{e.course_title || e.course_id}</td>
                    <td className="px-6 py-3 text-xs text-slate-500">
                      {new Date(e.enrolled_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-32 bg-slate-200 rounded-full h-2">
                          <div
                            className="bg-indigo-600 h-2 rounded-full"
                            style={{ width: `${e.progress_percentage}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-slate-700">{e.progress_percentage}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-3">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                        e.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" :
                        e.status === "IN_PROGRESS" ? "bg-indigo-100 text-indigo-800" : "bg-slate-100 text-slate-600"
                      }`}>
                        {e.status}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      {e.status !== "COMPLETED" && (
                        <button
                          onClick={() => handleUpdateProgress(e.id, e.progress_percentage)}
                          className="text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-semibold px-3 py-1 rounded"
                        >
                          Continue (+25%)
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

      {/* Tab: Certifications */}
      {activeTab === "certifications" && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
              <h3 className="font-semibold text-slate-900">Enterprise & Professional Certifications</h3>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {certifications?.map((c: any) => (
                <div key={c.id} className="p-4 rounded-lg border border-slate-200 bg-slate-50">
                  <p className="font-semibold text-slate-900">{c.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{c.issuing_body}</p>
                  <div className="mt-3 flex justify-between items-center text-xs">
                    <span className="font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                      Validity: {c.validity_months || 24} mos
                    </span>
                    <span className="text-emerald-700 font-semibold">{c.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Career & Opportunities */}
      {activeTab === "career" && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Internal Career Opportunities</h3>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              {opportunities?.map((opp: any) => (
                <div key={opp.id} className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-3">
                  <div className="flex justify-between items-start">
                    <h4 className="font-bold text-slate-900 text-base">{opp.title}</h4>
                    <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-semibold">
                      {opp.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 line-clamp-2">{opp.description}</p>
                  <div className="pt-2 flex justify-between items-center border-t border-slate-100">
                    <span className="text-xs text-slate-500">Skills: {opp.required_skills || "General"}</span>
                    <button
                      onClick={() => handleApplyOpportunity(opp.id)}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs px-3 py-1.5 rounded-lg font-medium"
                    >
                      Apply Now
                    </button>
                  </div>
                </div>
              ))}
              {(!opportunities || opportunities.length === 0) && (
                <p className="text-sm text-slate-400 col-span-2 text-center py-6">No open career opportunities posted.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Individual Development Plan */}
      {activeTab === "idp" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="font-semibold text-slate-900">Individual Development Plans (IDP)</h3>
          </div>
          <div className="p-6 space-y-4">
            {devPlans?.map((dp: any) => (
              <div key={dp.id} className="p-5 rounded-lg border border-slate-200 bg-slate-50 space-y-3">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-bold text-slate-900 text-base">{dp.current_role} → {dp.target_role || "Target Role"}</h4>
                    <p className="text-xs text-slate-500 mt-1">Review Period: {dp.review_period}</p>
                  </div>
                  <span className="text-xs bg-indigo-100 text-indigo-800 font-semibold px-2 py-0.5 rounded">
                    {dp.status}
                  </span>
                </div>
                {dp.employee_notes && (
                  <p className="text-xs text-slate-700 bg-white p-3 rounded border border-slate-200">
                    <span className="font-semibold">My Career Goals:</span> {dp.employee_notes}
                  </p>
                )}
                {dp.goals && dp.goals.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <p className="text-xs font-semibold text-slate-800">Development Milestones:</p>
                    {dp.goals.map((g: any) => (
                      <div key={g.id} className="text-xs flex justify-between items-center bg-white p-2 rounded border border-slate-200">
                        <span>{g.title}</span>
                        <span className="text-slate-400 font-mono">Due: {g.due_date || "Open"}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {(!devPlans || devPlans.length === 0) && (
              <p className="text-sm text-slate-400 text-center py-6">No individual development plan active.</p>
            )}
          </div>
        </div>
      )}

      {/* Tab: Mentoring */}
      {activeTab === "mentoring" && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Active Mentoring Programs</h3>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              {mentoringProgs?.map((prog: any) => (
                <div key={prog.id} className="p-4 rounded-lg border border-slate-200 bg-slate-50">
                  <p className="font-semibold text-slate-900">{prog.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{prog.description}</p>
                  <div className="mt-3 flex justify-between items-center text-xs">
                    <span className="font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                      Duration: {prog.duration_months} Months
                    </span>
                    <span className="text-emerald-700 font-semibold">{prog.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Admin Console */}
      {activeTab === "admin" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Analytics */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="font-semibold text-slate-900">Enterprise Learning Effectiveness Analytics</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500 font-medium">Total Courses</p>
                  <p className="text-xl font-bold text-slate-900 mt-1">{analytics?.total_courses ?? 0}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500 font-medium">Completion Rate</p>
                  <p className="text-xl font-bold text-indigo-600 mt-1">{analytics?.completion_rate_pct ?? 0}%</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500 font-medium">Training Hours</p>
                  <p className="text-xl font-bold text-emerald-600 mt-1">{analytics?.total_training_hours ?? 0} hrs</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500 font-medium">Compliance Rate</p>
                  <p className="text-xl font-bold text-amber-600 mt-1">{analytics?.mandatory_compliance_rate_pct ?? 100}%</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500 font-medium">Expiring Certs (30d)</p>
                  <p className="text-xl font-bold text-rose-600 mt-1">{analytics?.expiring_certifications_30d ?? 0}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-xs text-slate-500 font-medium">Mentoring Pairs</p>
                  <p className="text-xl font-bold text-purple-600 mt-1">{analytics?.active_mentoring_relationships ?? 0}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {/* Create Course Form */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="font-semibold text-slate-900 mb-4">Create New Course</h3>
              <form onSubmit={handleCreateCourse} className="space-y-4 text-sm">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Course Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CRS-SEC-101"
                    value={newCourseCode}
                    onChange={(e) => setNewCourseCode(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Title *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Threat Modeling & IAM"
                    value={newCourseTitle}
                    onChange={(e) => setNewCourseTitle(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">Category</label>
                    <select
                      value={newCourseCat}
                      onChange={(e) => setNewCourseCat(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="TECHNICAL">Technical</option>
                      <option value="COMPLIANCE">Compliance</option>
                      <option value="LEADERSHIP">Leadership</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">Difficulty</label>
                    <select
                      value={newCourseDiff}
                      onChange={(e) => setNewCourseDiff(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="BEGINNER">Beginner</option>
                      <option value="INTERMEDIATE">Intermediate</option>
                      <option value="ADVANCED">Advanced</option>
                    </select>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={submittingCourse}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
                >
                  {submittingCourse ? "Publishing..." : "Publish Course"}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
