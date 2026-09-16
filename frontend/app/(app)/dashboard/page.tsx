"use client";

import useSWR from "swr";
import { useAuth } from "@/lib/auth-context";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin",
  hr_admin: "HR Admin",
  hiring_manager: "Hiring Manager",
  finance: "Finance",
  employee: "Employee / Trainee",
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: candidates } = useSWR(
    user?.role !== "employee" && user?.role !== "finance" ? "/candidates" : null,
    fetcher
  );
  const { data: leave } = useSWR("/leave", fetcher, { onError: () => {} });
  const { data: attendance } = useSWR("/attendance", fetcher, { onError: () => {} });

  const stats = [
    {
      label: "Candidates",
      value: candidates?.length ?? "—",
      icon: "👤",
      color: "bg-blue-50 text-blue-700",
      hide: user?.role === "employee" || user?.role === "finance",
    },
    {
      label: "Leave Requests",
      value: leave?.length ?? "—",
      icon: "🏖️",
      color: "bg-amber-50 text-amber-700",
    },
    {
      label: "Attendance Records",
      value: attendance?.length ?? "—",
      icon: "📅",
      color: "bg-green-50 text-green-700",
    },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-1">Dashboard</h2>
      <p className="text-gray-500 text-sm mb-8">
        Welcome back,{" "}
        <span className="font-medium text-indigo-700">{user?.email}</span>{" "}
        &mdash; {ROLE_LABEL[user?.role ?? ""] ?? user?.role}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-10">
        {stats
          .filter((s) => !s.hide)
          .map((s) => (
            <div key={s.label} className={`rounded-xl p-6 ${s.color} flex items-center gap-4`}>
              <span className="text-3xl">{s.icon}</span>
              <div>
                <p className="text-2xl font-bold">{s.value}</p>
                <p className="text-sm font-medium">{s.label}</p>
              </div>
            </div>
          ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="font-semibold text-gray-700 mb-3">Quick Actions</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {user?.role !== "employee" && user?.role !== "finance" && (
            <a href="/candidates" className="btn-quick">➕ New Candidate</a>
          )}
          <a href="/attendance" className="btn-quick">📅 Log Attendance</a>
          <a href="/leave" className="btn-quick">🏖️ Request Leave</a>
          <a href="/documents" className="btn-quick">📄 Upload Document</a>
        </div>
      </div>
    </div>
  );
}
