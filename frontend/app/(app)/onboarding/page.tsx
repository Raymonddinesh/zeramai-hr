"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function OnboardingPage() {
  const { data: templates } = useSWR("/onboarding/templates", fetcher);
  const { data: candidates } = useSWR("/candidates", fetcher);
  const [selectedProcess, setSelectedProcess] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const startOnboarding = async (candidateId: string, templateId: string) => {
    setLoading(true);
    try {
      const res = await api.post("/onboarding/process", {
        candidate_id: candidateId,
        template_id: templateId,
      });
      setSelectedProcess(res.data);
    } catch {
      alert("Error initiating onboarding");
    } finally {
      setLoading(false);
    }
  };

  const completeTask = async (taskId: string) => {
    try {
      const res = await api.patch(`/onboarding/tasks/${taskId}/complete`);
      if (selectedProcess) {
        setSelectedProcess({
          ...selectedProcess,
          completion_percentage: res.data.new_completion_percentage,
          tasks: selectedProcess.tasks.map((t: any) =>
            t.id === taskId ? { ...t, status: "completed" } : t
          ),
        });
      }
    } catch {
      alert("Error completing task");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Onboarding & Preboarding Engine</h2>
        <p className="text-gray-500 text-sm">
          Phase 2: Automated onboarding workflows, task checklists (IT, HR, Compliance) & real-time completion tracking
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Templates Panel */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-200">
          <h3 className="font-semibold text-gray-800 mb-3">Onboarding Templates</h3>
          <div className="space-y-3">
            {(templates || []).map((t: any) => (
              <div key={t.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex justify-between items-center mb-1">
                  <h4 className="font-semibold text-gray-900 text-sm">{t.name}</h4>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                    {t.checklist_items?.length || 0} Tasks
                  </span>
                </div>
                <p className="text-xs text-gray-500 mb-2">{t.description || "Standard company onboarding plan"}</p>
                <div className="text-[11px] text-gray-600 space-y-1">
                  {(t.checklist_items || []).slice(0, 3).map((item: any, i: number) => (
                    <div key={i} className="flex items-center gap-1.5 truncate">
                      <span className="text-indigo-500 font-bold">•</span>
                      <span className="truncate">{item.task_title}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-gray-100">
            <h4 className="font-medium text-xs text-gray-500 uppercase tracking-wider mb-2">
              Launch for Selected Candidate
            </h4>
            <div className="space-y-2">
              {(candidates || []).filter((c: any) => c.status === "selected" || c.status === "applied").slice(0, 3).map((c: any) => (
                <button
                  key={c.id}
                  disabled={loading || !templates?.length}
                  onClick={() => startOnboarding(c.id, templates[0].id)}
                  className="w-full text-left p-2.5 bg-indigo-50/70 hover:bg-indigo-100/70 border border-indigo-200 rounded-lg text-xs transition"
                >
                  <p className="font-semibold text-indigo-900">{c.person?.full_name || c.applied_position}</p>
                  <p className="text-indigo-600">Start Onboarding →</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Process Detail & Interactive Tasks */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <h3 className="font-semibold text-gray-800 mb-2">Live Onboarding Checklist</h3>
          {selectedProcess ? (
            <div className="space-y-4">
              <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-semibold text-indigo-900">Overall Progress</span>
                  <span className="text-lg font-bold text-indigo-700">
                    {Math.round(selectedProcess.completion_percentage)}%
                  </span>
                </div>
                <div className="w-full bg-indigo-200 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${selectedProcess.completion_percentage}%` }}
                  ></div>
                </div>
                <p className="text-xs text-indigo-700 mt-2">
                  Status: <span className="font-semibold uppercase">{selectedProcess.status}</span>
                </p>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Assigned Checklist Tasks ({selectedProcess.tasks?.length || 0})
                </h4>
                {(selectedProcess.tasks || []).map((t: any) => (
                  <div
                    key={t.id}
                    className={`p-3.5 rounded-xl border flex items-center justify-between transition ${
                      t.status === "completed"
                        ? "bg-gray-50 border-gray-200 opacity-80"
                        : "bg-white border-gray-300 shadow-sm"
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            t.status === "completed"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {t.status}
                        </span>
                        <h5
                          className={`text-sm font-semibold ${
                            t.status === "completed" ? "line-through text-gray-500" : "text-gray-900"
                          }`}
                        >
                          {t.title}
                        </h5>
                      </div>
                      <p className="text-xs text-gray-500">
                        Category: <span className="capitalize">{t.category}</span> • Assignee:{" "}
                        <span className="capitalize">{t.assignee_role?.replace("_", " ")}</span>
                      </p>
                    </div>

                    {t.status !== "completed" && (
                      <button
                        onClick={() => completeTask(t.id)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-3 py-1.5 rounded-lg font-medium shadow-sm transition"
                      >
                        ✓ Mark Done
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-gray-400">
              <span className="text-4xl block mb-2">📋</span>
              <p className="text-sm font-medium">Select a candidate on the left to view and execute their onboarding process</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
