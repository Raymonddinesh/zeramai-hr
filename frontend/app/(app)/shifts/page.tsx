"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function ShiftsPage() {
  const { data: templates } = useSWR("/shifts/templates", fetcher);
  const { data: roster, mutate: mutateRoster } = useSWR(
    "/shifts/roster?start_date=2026-10-01&end_date=2026-10-31",
    fetcher
  );
  const { data: candidates } = useSWR("/candidates", fetcher);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [assignDate, setAssignDate] = useState("2026-10-05");

  const handleAssignShift = async (personId: string) => {
    if (!selectedTemplate && templates?.length) {
      setSelectedTemplate(templates[0].id);
    }
    const templateId = selectedTemplate || templates?.[0]?.id;
    if (!templateId) return alert("Please select a shift template first");

    try {
      await api.post("/shifts/assign", {
        person_id: personId,
        shift_template_id: templateId,
        date: assignDate,
      });
      alert("Shift assigned successfully with conflict detection passed!");
      mutateRoster();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Conflict detected: Person already assigned on this date");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Attendance & Shift Rostering</h2>
        <p className="text-gray-500 text-sm">
          Phase 4: Multi-shift templates, conflict detection, automated roster calendar & peer shift swaps
        </p>
      </div>

      {/* Templates Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {(templates || []).map((t: any) => (
          <div
            key={t.id}
            onClick={() => setSelectedTemplate(t.id)}
            className={`cursor-pointer rounded-xl p-4 border transition ${
              selectedTemplate === t.id
                ? "border-indigo-600 bg-indigo-50/50 shadow-md ring-2 ring-indigo-200"
                : "border-gray-200 bg-white hover:border-gray-300 shadow-sm"
            }`}
          >
            <div className="flex justify-between items-center mb-1">
              <h4 className="font-semibold text-gray-900 text-sm">{t.name}</h4>
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: t.color_code || "#3B82F6" }}
              ></span>
            </div>
            <p className="text-xs text-gray-500 mb-2">
              ⏰ {t.start_time} - {t.end_time}
            </p>
            <div className="flex justify-between items-center text-[11px] text-gray-600">
              <span className="capitalize">{t.shift_type}</span>
              <span>{t.is_night_shift ? "🌙 Night" : "☀️ Day"}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Assign Panel */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-200">
          <h3 className="font-semibold text-gray-800 mb-3">Schedule Worker to Shift</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Date to Assign</label>
              <input
                type="date"
                value={assignDate}
                onChange={(e) => setAssignDate(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-800"
              />
            </div>

            <div className="pt-2">
              <p className="text-xs font-medium text-gray-500 mb-2">Assign Team Member:</p>
              <div className="space-y-2">
                {(candidates || []).slice(0, 4).map((c: any) => (
                  <button
                    key={c.id}
                    onClick={() => handleAssignShift(c.person_id)}
                    className="w-full text-left p-2.5 bg-gray-50 hover:bg-indigo-50 border border-gray-200 rounded-lg text-xs transition flex justify-between items-center"
                  >
                    <span className="font-semibold text-gray-800">{c.person?.full_name || "Employee"}</span>
                    <span className="text-indigo-600 font-medium">+ Assign →</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Live Roster Calendar */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-5 border border-gray-200">
          <h3 className="font-semibold text-gray-800 mb-3">Active Roster Calendar (October 2026)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase border-b">
                <tr>
                  <th className="px-4 py-2.5">Date</th>
                  <th className="px-4 py-2.5">Shift Type</th>
                  <th className="px-4 py-2.5">Person ID</th>
                  <th className="px-4 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y text-gray-700">
                {(roster || []).map((r: any) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono font-medium text-gray-900">{r.date}</td>
                    <td className="px-4 py-2.5">
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded font-medium">
                        Standard Shift
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-gray-500 truncate max-w-[120px]">{r.person_id}</td>
                    <td className="px-4 py-2.5">
                      <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-medium">
                        Assigned
                      </span>
                    </td>
                  </tr>
                ))}
                {(!roster || roster.length === 0) && (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-gray-400">
                      No shift assignments found for this period.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
