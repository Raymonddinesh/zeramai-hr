"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function PerformancePage() {
  const { data: cycles } = useSWR("/performance/cycles", fetcher);
  const { data: candidates } = useSWR("/candidates", fetcher);
  const [selectedPerson, setSelectedPerson] = useState<string>("");
  const { data: objectives, mutate: mutateObjectives } = useSWR(
    selectedPerson ? `/performance/objectives/${selectedPerson}` : null,
    fetcher
  );

  const [newTitle, setNewTitle] = useState("");

  const handleCreateObjective = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPerson || !newTitle) return;
    try {
      await api.post("/performance/objectives", {
        person_id: selectedPerson,
        title: newTitle,
        weight: 1.0,
      });
      setNewTitle("");
      mutateObjectives();
      alert("Objective created successfully!");
    } catch {
      alert("Error creating objective");
    }
  };

  const handleUpdateProgress = async (krId: string, currentVal: number) => {
    try {
      await api.patch(`/performance/kr/${krId}/progress?current_value=${currentVal}`);
      mutateObjectives();
    } catch {
      alert("Error updating progress");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Performance, Goals & OKRs</h2>
        <p className="text-gray-500 text-sm">
          Phase 7: Company objectives, measurable key results with auto-recalculated progress & 360 review cycles
        </p>
      </div>

      {/* Review Cycles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(cycles || []).map((c: any) => (
          <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex justify-between items-center mb-1">
              <h4 className="font-bold text-gray-900 text-sm">{c.name}</h4>
              <span className="text-[10px] font-bold uppercase px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
                {c.cycle_type}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              📅 {c.start_date} to {c.end_date}
            </p>
            <div className="mt-2 text-xs font-semibold text-indigo-600 uppercase">
              Status: {c.status}
            </div>
          </div>
        ))}
      </div>

      {/* Select Person to view OKRs */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200 space-y-4">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div>
            <h3 className="font-semibold text-gray-800">Employee OKR Management</h3>
            <p className="text-xs text-gray-500">Select an employee to inspect and update their quarterly goals</p>
          </div>
          <select
            value={selectedPerson}
            onChange={(e) => setSelectedPerson(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800"
          >
            <option value="">-- Choose Employee --</option>
            {(candidates || []).map((c: any) => (
              <option key={c.person_id} value={c.person_id}>
                {c.person?.full_name || "Employee"} ({c.applied_position || "Team Member"})
              </option>
            ))}
          </select>
        </div>

        {selectedPerson && (
          <form onSubmit={handleCreateObjective} className="flex gap-3 pt-2">
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Add new objective (e.g. Reduce infrastructure latency by 30%)"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800"
            />
            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              + Add Goal
            </button>
          </form>
        )}

        {/* Objectives List */}
        <div className="space-y-4 pt-2">
          {(objectives || []).map((obj: any) => (
            <div key={obj.id} className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-bold text-gray-900 text-base">{obj.title}</h4>
                  <span className="text-xs text-gray-500 font-medium">Status: {obj.status?.toUpperCase()}</span>
                </div>
                <div className="text-right">
                  <span className="text-xl font-extrabold text-indigo-600">{Math.round(obj.progress_pct)}%</span>
                  <p className="text-[10px] text-gray-400 uppercase font-semibold">Progress</p>
                </div>
              </div>

              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${obj.progress_pct}%` }}
                ></div>
              </div>
            </div>
          ))}

          {selectedPerson && (!objectives || objectives.length === 0) && (
            <div className="text-center py-8 text-gray-400 text-sm">
              No objectives found for this employee. Add one above!
            </div>
          )}

          {!selectedPerson && (
            <div className="text-center py-10 text-gray-400 text-sm">
              Please choose an employee from the dropdown above to view their OKR dashboard.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
