"use client";

import { useState } from "react";
import useSWR from "swr";
import axios from "axios";
import api, { leaveApi } from "@/lib/api";

interface LeaveRecord {
  id: string;
  person_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  days: number;
  status: string;
  reason?: string;
}

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  cancelled: "bg-gray-100 text-gray-600",
};

export default function LeavePage() {
  const { data, mutate } = useSWR<LeaveRecord[]>("/leave", fetcher);
  const [form, setForm] = useState({ person_id: "", leave_type: "casual", start_date: "", end_date: "", days: "1", reason: "" });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg("");
    try {
      await leaveApi.create({ ...form, days: parseFloat(form.days) });
      await mutate();
      setMsg("✅ Leave request submitted");
      setForm({ ...form, start_date: "", end_date: "", reason: "" });
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
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Leave Management</h2>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 mb-6 grid grid-cols-2 gap-4">
        <h3 className="col-span-2 font-semibold text-gray-700">New Leave Request</h3>
        {msg && <p className="col-span-2 text-sm">{msg}</p>}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Person ID</label>
          <input required value={form.person_id} onChange={(e) => setForm({ ...form, person_id: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="UUID" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Leave Type</label>
          <select value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            {["casual","sick","earned","unpaid","maternity","paternity","other"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Start Date</label>
          <input type="date" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">End Date</label>
          <input type="date" required value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Days</label>
          <input type="number" step="0.5" min="0.5" required value={form.days} onChange={(e) => setForm({ ...form, days: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Reason</label>
          <input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="col-span-2">
          <button type="submit" disabled={submitting}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {submitting ? "Submitting…" : "Submit Request"}
          </button>
        </div>
      </form>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["Person","Type","Start","End","Days","Status","Reason"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!data && <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>}
            {data?.length === 0 && <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No requests</td></tr>}
            {data?.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.person_id.slice(0,8)}…</td>
                <td className="px-4 py-3 capitalize">{r.leave_type}</td>
                <td className="px-4 py-3">{r.start_date}</td>
                <td className="px-4 py-3">{r.end_date}</td>
                <td className="px-4 py-3">{r.days}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[r.status]}`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{r.reason ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
