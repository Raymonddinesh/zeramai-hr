"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function LearningPage() {
  const { data: courses } = useSWR("/lms/courses", fetcher);
  const { data: candidates } = useSWR("/candidates", fetcher);
  const [selectedPerson, setSelectedPerson] = useState("");
  const { data: enrollments, mutate: mutateEnrollments } = useSWR(
    selectedPerson ? `/lms/enrollments/${selectedPerson}` : null,
    fetcher
  );
  const { data: certificates } = useSWR(
    selectedPerson ? `/lms/certificates/${selectedPerson}` : null,
    fetcher
  );

  const handleEnroll = async (courseId: string) => {
    if (!selectedPerson) return alert("Select an employee first");
    try {
      await api.post("/lms/enroll", {
        course_id: courseId,
        person_id: selectedPerson,
      });
      alert("Enrolled successfully in course!");
      mutateEnrollments();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Enrollment failed");
    }
  };

  const handleCompleteCourse = async (enrollmentId: string) => {
    try {
      await api.patch(`/lms/enrollments/${enrollmentId}/progress?progress_pct=100&score=95`);
      alert("Course completed! Certificate auto-generated.");
      mutateEnrollments();
    } catch {
      alert("Error updating progress");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Learning Management & Skills (LMS)</h2>
        <p className="text-gray-500 text-sm">
          Phase 8: Training courses, modular learning paths, completion tracking & automated certification
        </p>
      </div>

      {/* Select Learner */}
      <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-200 flex flex-col sm:flex-row justify-between items-center gap-4">
        <div>
          <h3 className="font-semibold text-gray-800 text-sm">Learner Profile</h3>
          <p className="text-xs text-gray-500">Select employee to manage enrollments and view issued certificates</p>
        </div>
        <select
          value={selectedPerson}
          onChange={(e) => setSelectedPerson(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800"
        >
          <option value="">-- Choose Learner --</option>
          {(candidates || []).map((c: any) => (
            <option key={c.person_id} value={c.person_id}>
              {c.person?.full_name || "Employee"} ({c.applied_position || "Team Member"})
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Course Catalog */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="font-semibold text-gray-800">Available Course Catalog</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(courses || []).map((c: any) => (
              <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-bold text-gray-900 text-base">{c.title}</h4>
                    <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium">
                      {c.category || "Professional Development"}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 font-medium">⏳ {c.duration_hours || 10} hrs</span>
                </div>
                <p className="text-xs text-gray-600 line-clamp-2">
                  {c.description || "Interactive enterprise modules covering core competencies and compliance standards."}
                </p>
                <button
                  onClick={() => handleEnroll(c.id)}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs py-2 rounded-lg font-medium shadow-sm transition"
                >
                  + Enroll Learner
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Enrollments & Certificates */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-200 space-y-3">
            <h3 className="font-semibold text-gray-800 text-sm">Active Enrollments</h3>
            {(enrollments || []).map((e: any) => (
              <div key={e.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-gray-900">{e.course?.title || "Enrolled Course"}</span>
                  <span className="text-indigo-600 font-bold">{Math.round(e.progress_pct)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-1.5 rounded-full"
                    style={{ width: `${e.progress_pct}%` }}
                  ></div>
                </div>
                {e.status !== "completed" ? (
                  <button
                    onClick={() => handleCompleteCourse(e.id)}
                    className="w-full text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 py-1 rounded font-semibold transition"
                  >
                    ✓ Mark 100% & Generate Certificate
                  </button>
                ) : (
                  <span className="text-[11px] font-bold text-emerald-700 flex items-center gap-1">
                    ✓ Completed & Certified
                  </span>
                )}
              </div>
            ))}
            {(!enrollments || enrollments.length === 0) && (
              <p className="text-xs text-gray-400 text-center py-4">No active enrollments for this learner.</p>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-200 space-y-3">
            <h3 className="font-semibold text-gray-800 text-sm">Issued Certificates</h3>
            {(certificates || []).map((cert: any) => (
              <div key={cert.id} className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🎓</span>
                  <div>
                    <h5 className="font-mono font-bold text-xs text-amber-900">{cert.certificate_number}</h5>
                    <p className="text-[11px] text-amber-700">Issued on: {cert.issued_date}</p>
                  </div>
                </div>
              </div>
            ))}
            {(!certificates || certificates.length === 0) && (
              <p className="text-xs text-gray-400 text-center py-4">No certificates issued yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
