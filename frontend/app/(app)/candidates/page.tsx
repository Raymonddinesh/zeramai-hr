"use client";

import { useState } from "react";
import useSWR from "swr";
import axios from "axios";
import api, { candidatesApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface Candidate {
  id: string;
  person_id: string;
  applied_position?: string;
  department?: string;
  status: string;
}

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-gray-100 text-gray-600",
  screening: "bg-yellow-100 text-yellow-700",
  interview: "bg-blue-100 text-blue-700",
  selected: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  converted_to_trainee: "bg-indigo-100 text-indigo-700",
};

export default function CandidatesPage() {
  const { user } = useAuth();
  const { data: candidates, mutate } = useSWR<Candidate[]>("/candidates", fetcher);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<{ full_name: string; email: string; applied_position: string; department: string }>({
    full_name: "",
    email: "",
    applied_position: "",
    department: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const canCreate = user?.role === "super_admin" || user?.role === "hr_admin";

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await candidatesApi.create(form);
      await mutate();
      setShowForm(false);
      setForm({ full_name: "", email: "", applied_position: "", department: "" });
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail ?? "Failed to create candidate");
      } else {
        setError("Failed to create candidate");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleSelect = async (id: string) => {
    await candidatesApi.select(id).catch(() => {});
    mutate();
  };

  const formFields: Array<{ key: keyof typeof form; label: string; required?: boolean; type?: string }> = [
    { key: "full_name", label: "Full Name", required: true },
    { key: "email", label: "Email", required: true, type: "email" },
    { key: "applied_position", label: "Applied Position" },
    { key: "department", label: "Department" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Candidates</h2>
        {canCreate && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
          >
            {showForm ? "Cancel" : "➕ Add Candidate"}
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-6 space-y-4">
          <h3 className="font-semibold text-gray-700">New Candidate</h3>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <div className="grid grid-cols-2 gap-4">
            {formFields.map(({ key, label, required, type }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-600 mb-1">{label}</label>
                <input
                  type={type ?? "text"}
                  required={required}
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
            ))}
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Create Candidate"}
          </button>
        </form>
      )}

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              {["Name", "Position", "Department", "Status", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!candidates && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
            )}
            {candidates?.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No candidates yet</td></tr>
            )}
            {candidates?.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-800">{c.person_id?.slice(0, 8)}…</td>
                <td className="px-4 py-3 text-gray-600">{c.applied_position ?? "—"}</td>
                <td className="px-4 py-3 text-gray-600">{c.department ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[c.status] ?? "bg-gray-100 text-gray-600"}`}>
                    {c.status.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {c.status === "applied" && (user?.role === "super_admin" || user?.role === "hr_admin" || user?.role === "hiring_manager") && (
                    <button
                      onClick={() => handleSelect(c.id)}
                      className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200"
                    >
                      Mark Selected
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
