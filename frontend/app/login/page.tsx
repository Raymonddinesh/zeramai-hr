"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      window.location.href = "/dashboard";
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  const setDemoUser = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("ChangeMe123!");
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="bg-white shadow-md rounded-xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-center text-indigo-700 mb-1">Zeramai HR</h1>
        <p className="text-center text-gray-500 text-sm mb-6">Sign in to your account</p>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 text-gray-800"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 text-gray-800"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider text-center mb-3">
            Quick Demo Login Accounts
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setDemoUser("superadmin@zeramai.com")}
              className="px-2.5 py-1.5 border border-indigo-200 text-indigo-700 bg-indigo-50/60 hover:bg-indigo-100/70 rounded-md font-medium text-center transition"
            >
              Super Admin
            </button>
            <button
              type="button"
              onClick={() => setDemoUser("hr@zeramai.com")}
              className="px-2.5 py-1.5 border border-blue-200 text-blue-700 bg-blue-50/60 hover:bg-blue-100/70 rounded-md font-medium text-center transition"
            >
              HR Admin
            </button>
            <button
              type="button"
              onClick={() => setDemoUser("manager@zeramai.com")}
              className="px-2.5 py-1.5 border border-emerald-200 text-emerald-700 bg-emerald-50/60 hover:bg-emerald-100/70 rounded-md font-medium text-center transition"
            >
              Hiring Manager
            </button>
            <button
              type="button"
              onClick={() => setDemoUser("employee@example.com")}
              className="px-2.5 py-1.5 border border-purple-200 text-purple-700 bg-purple-50/60 hover:bg-purple-100/70 rounded-md font-medium text-center transition"
            >
              Employee Self-Service
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
