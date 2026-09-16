"use client";

import { useState } from "react";
import useSWR from "swr";
import axios from "axios";
import api, { stipendsApi } from "@/lib/api";

interface StipendRecord {
  id: string;
  person_id: string;
  month: string;
  amount: number;
  currency: string;
  status: string;
}

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  approved: "bg-blue-100 text-blue-700",
  paid: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-600",
};

export default function StipendsPage() {
  const { data, mutate } = useSWR<StipendRecord[]>("/stipends", fetcher);
  const [form, setForm] = useState({ person_id: "", month: "", amount: "", currency: "INR", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState("");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg("");
    try {
      await stipendsApi.create({ ...form, amount: parseFloat(form.amount) });
      await mutate();
      setMsg("✅ Stipend created");
      setForm({ ...form, month: "", amount: "", notes: "" });
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

  const handleApprove = async (id: string) => {
    try {
      await stipendsApi.approve(id);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        alert(err.response?.data?.detail ?? "Failed");
      } else {
        alert("Failed");
      }
    }
    mutate();
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Stipends</h2>

      <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-6 grid grid-cols-2 gap-4">
        <h3 className="col-span-2 font-semibold text-gray-700">Create Stipend</h3>
        {msg && <p className="col-span-2 text-sm">{msg}</p>}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Person ID</label>
          <input required value={form.person_id} onChange={(e) => setForm({ ...form, person_id: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="UUID" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Month (YYYY-MM)</label>
          <input required value={form.month} onChange={(e) => setForm({ ...form, month: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="2026-09" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Amount</label>
          <input type="number" required min="0" step="0.01" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Currency</label>
          <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            {["INR","USD","EUR"].map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div className="col-span-2">
          <button type="submit" disabled={submitting}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {submitting ? "Saving…" : "Create Stipend"}
          </button>
        </div>
      </form>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["Person","Month","Amount","Status","Actions"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!data && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>}
            {data?.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No stipends</td></tr>}
            {data?.map((s) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{s.person_id.slice(0,8)}…</td>
                <td className="px-4 py-3">{s.month}</td>
                <td className="px-4 py-3 font-semibold">{s.currency} {Number(s.amount).toLocaleString()}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s.status]}`}>
                    {s.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {s.status === "pending" && (
                    <button onClick={() => handleApprove(s.id)}
                      className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200">
                      Approve
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
