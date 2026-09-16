"use client";

import { useState } from "react";
import useSWR from "swr";
import axios from "axios";
import api, { attendanceApi } from "@/lib/api";

interface AttendanceRecord {
  id: string;
  person_id: string;
  date: string;
  status: string;
  notes?: string;
}

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const STATUS_COLOR: Record<string, string> = {
  present: "bg-green-100 text-green-700",
  absent: "bg-red-100 text-red-700",
  half_day: "bg-yellow-100 text-yellow-700",
  on_leave: "bg-blue-100 text-blue-700",
  holiday: "bg-purple-100 text-purple-700",
};

export default function AttendancePage() {
  const { data, mutate } = useSWR<AttendanceRecord[]>("/attendance", fetcher);
  const [form, setForm] = useState({ person_id: "", date: "", status: "present", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg("");
    try {
      await attendanceApi.create(form);
      await mutate();
      setMsg("✅ Record saved");
      setForm({ ...form, date: "", notes: "" });
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setMsg("❌ " + (err.response?.data?.detail ?? "Failed"));
      } else {
        setMsg("❌ Failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Attendance</h2>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 mb-6 grid grid-cols-2 gap-4">
        <h3 className="col-span-2 font-semibold text-gray-700">Log Attendance</h3>
        {msg && <p className="col-span-2 text-sm">{msg}</p>}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Person ID</label>
          <input required value={form.person_id} onChange={(e) => setForm({ ...form, person_id: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="UUID" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Date</label>
          <input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Status</label>
          <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            {["present","absent","half_day","on_leave","holiday"].map((s) => (
              <option key={s} value={s}>{s.replace(/_/g," ")}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Notes</label>
          <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="col-span-2">
          <button type="submit" disabled={submitting}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {submitting ? "Saving…" : "Log Attendance"}
          </button>
        </div>
      </form>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["Person ID","Date","Status","Notes"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!data && <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>}
            {data?.length === 0 && <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">No records</td></tr>}
            {data?.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.person_id.slice(0,8)}…</td>
                <td className="px-4 py-3">{r.date}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[r.status]}`}>
                    {r.status.replace(/_/g," ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{r.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
