"use client";

import { useState } from "react";
import useSWR from "swr";
import axios from "axios";
import api, { evaluationsApi } from "@/lib/api";

interface EvaluationRecord {
  id: string;
  person_id: string;
  period_start: string;
  period_end: string;
  overall_rating?: number;
  status: string;
}

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const STATUS_COLOR: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  submitted: "bg-blue-100 text-blue-700",
  acknowledged: "bg-green-100 text-green-700",
};

export default function EvaluationsPage() {
  const { data, mutate } = useSWR<EvaluationRecord[]>("/evaluations", fetcher);
  const [form, setForm] = useState({ person_id: "", period_start: "", period_end: "", overall_rating: "", comments: "" });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState("");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg("");
    try {
      await evaluationsApi.create({
        ...form,
        overall_rating: form.overall_rating ? parseFloat(form.overall_rating) : undefined,
      });
      await mutate();
      setMsg("✅ Evaluation created");
      setForm({ person_id: "", period_start: "", period_end: "", overall_rating: "", comments: "" });
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

  const handleSubmitEval = async (id: string) => {
    await evaluationsApi.submit(id, {}).catch(() => {});
    mutate();
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Evaluations</h2>

      <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-6 grid grid-cols-2 gap-4">
        <h3 className="col-span-2 font-semibold text-gray-700">New Evaluation</h3>
        {msg && <p className="col-span-2 text-sm">{msg}</p>}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Person ID</label>
          <input required value={form.person_id} onChange={(e) => setForm({ ...form, person_id: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="UUID" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Overall Rating (1–5)</label>
          <input type="number" step="0.5" min="1" max="5" value={form.overall_rating}
            onChange={(e) => setForm({ ...form, overall_rating: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Period Start</label>
          <input type="date" required value={form.period_start} onChange={(e) => setForm({ ...form, period_start: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Period End</label>
          <input type="date" required value={form.period_end} onChange={(e) => setForm({ ...form, period_end: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-600 mb-1">Comments</label>
          <textarea value={form.comments} onChange={(e) => setForm({ ...form, comments: e.target.value })}
            rows={3} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div className="col-span-2">
          <button type="submit" disabled={submitting}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {submitting ? "Saving…" : "Create Evaluation"}
          </button>
        </div>
      </form>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["Person","Period","Rating","Status","Actions"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!data && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>}
            {data?.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No evaluations</td></tr>}
            {data?.map((e) => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{e.person_id.slice(0,8)}…</td>
                <td className="px-4 py-3 text-gray-600">{e.period_start} → {e.period_end}</td>
                <td className="px-4 py-3">{e.overall_rating ?? "—"} / 5</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[e.status]}`}>
                    {e.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {e.status === "draft" && (
                    <button onClick={() => handleSubmitEval(e.id)}
                      className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200">
                      Submit
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
