"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function JobsPage() {
  const { data: jobs, mutate: mutateJobs } = useSWR("/jobs", fetcher);
  const { data: candidates } = useSWR("/candidates", fetcher);
  const [showCreateJob, setShowCreateJob] = useState(false);
  const [selectedJob, setSelectedJob] = useState<any>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("Engineering");
  const [location, setLocation] = useState("Bangalore, India");
  const [skills, setSkills] = useState("Python, FastAPI, Next.js");
  const [minExp, setMinExp] = useState(2);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/jobs", {
        title,
        department,
        location,
        required_skills: skills.split(",").map((s) => s.trim()),
        min_experience_years: Number(minExp),
      });
      setTitle("");
      setShowCreateJob(false);
      mutateJobs();
    } catch {
      alert("Error creating job requisition");
    }
  };

  const handleApplyWithAI = async (jobId: string, candidateId: string) => {
    try {
      const res = await api.post(`/jobs/${jobId}/apply`, {
        candidate_id: candidateId,
        resume_text: "Experienced software engineer with 4 years building scalable microservices with Python, FastAPI, and React.",
        candidate_experience_years: 4,
      });
      alert(`Candidate applied! AI Match Score: ${res.data.ai_match_score}%\nReasons: ${res.data.ai_match_reasons?.join(", ")}`);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error applying to job");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Talent Acquisition & Global ATS</h2>
          <p className="text-gray-500 text-sm">
            Phase 3: Job requisitions, AI resume match scoring, interview schedules, scorecards & offer management
          </p>
        </div>
        <button
          onClick={() => setShowCreateJob(!showCreateJob)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm"
        >
          {showCreateJob ? "Cancel" : "+ Post Job Requisition"}
        </button>
      </div>

      {showCreateJob && (
        <form onSubmit={handleCreateJob} className="bg-white p-6 rounded-xl border border-indigo-100 shadow-sm space-y-4">
          <h3 className="font-semibold text-gray-800">Create New Job Opening</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Job Title</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Senior Backend Architect"
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-800"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Department</label>
              <input
                type="text"
                required
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-800"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Location</label>
              <input
                type="text"
                required
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-800"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Required Skills (comma separated)</label>
              <input
                type="text"
                required
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-800"
              />
            </div>
          </div>
          <button type="submit" className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
            Publish Job Opening
          </button>
        </form>
      )}

      {/* Jobs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {(jobs || []).map((j: any) => (
          <div key={j.id} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-3">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-bold text-gray-900 text-base">{j.title}</h4>
                <p className="text-xs text-gray-500">{j.department} • {j.location}</p>
              </div>
              <span className="px-2 py-0.5 bg-green-100 text-green-800 text-[11px] font-bold rounded uppercase">
                {j.status}
              </span>
            </div>

            <div>
              <p className="text-xs text-gray-500 font-medium mb-1">Required Skills:</p>
              <div className="flex flex-wrap gap-1.5">
                {(j.required_skills || []).map((s: string, idx: number) => (
                  <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                    {s}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-gray-100">
              <p className="text-[11px] font-semibold text-gray-500 uppercase mb-2">Test AI Resume Match with Candidate:</p>
              <div className="space-y-1">
                {(candidates || []).slice(0, 2).map((c: any) => (
                  <button
                    key={c.id}
                    onClick={() => handleApplyWithAI(j.id, c.id)}
                    className="w-full text-left text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-2.5 py-1.5 rounded transition flex justify-between items-center"
                  >
                    <span>{c.person?.full_name || "Applicant"}</span>
                    <span className="font-semibold">Match Score →</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
