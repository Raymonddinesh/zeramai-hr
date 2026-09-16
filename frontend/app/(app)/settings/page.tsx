"use client";

import useSWR from "swr";
import api from "@/lib/api";
import { useState } from "react";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function SettingsPage() {
  const { data: securityPolicy, mutate: mutateSec } = useSWR("/security/policy", fetcher);
  const { data: sessions, mutate: mutateSessions } = useSWR("/security/sessions", fetcher);
  const { data: calendars } = useSWR("/localization/calendars", fetcher);
  const { data: candidates } = useSWR("/candidates", fetcher);

  const [activeTab, setActiveTab] = useState<"security" | "custom_fields" | "localization" | "ai_suite">("security");

  // Currency Converter state
  const [fromCurr, setFromCurr] = useState("USD");
  const [toCurr, setToCurr] = useState("INR");
  const [currAmount, setCurrAmount] = useState(1000);
  const [convertedResult, setConvertedResult] = useState<any>(null);

  // AI Helpdesk test
  const [helpdeskQuestion, setHelpdeskQuestion] = useState("How many casual leave days do I get?");
  const [aiAnswer, setAiAnswer] = useState<any>(null);

  // AI Attrition prediction
  const [selectedPersonForAi, setSelectedPersonForAi] = useState("");
  const [attritionResult, setAttritionResult] = useState<any>(null);

  const handleConvertCurrency = async () => {
    try {
      const res = await api.get(`/localization/currencies/convert?from_currency=${fromCurr}&to_currency=${toCurr}&amount=${currAmount}`);
      setConvertedResult(res.data);
    } catch {
      alert("Currency conversion rate not found");
    }
  };

  const handleAskHelpdesk = async () => {
    try {
      const res = await api.post("/ai/helpdesk/ask", { question: helpdeskQuestion });
      setAiAnswer(res.data);
    } catch {
      alert("Error asking AI Helpdesk");
    }
  };

  const handlePredictAttrition = async () => {
    if (!selectedPersonForAi) return alert("Select an employee first");
    try {
      const res = await api.post(`/ai/predict-attrition/${selectedPersonForAi}`);
      setAttritionResult(res.data);
    } catch {
      alert("Error generating predictive model assessment");
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await api.post(`/security/sessions/${sessionId}/revoke`);
      alert("Session revoked successfully!");
      mutateSessions();
    } catch {
      alert("Error revoking session");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Enterprise Administration & Security</h2>
        <p className="text-gray-500 text-sm">
          Phases 11-15: Master PRD Enterprise IAM, Active Sessions, Multi-Country Localization, and Governed AI Suite
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        <button
          onClick={() => setActiveTab("security")}
          className={`px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap transition ${
            activeTab === "security" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          🔒 IAM & Security Controls
        </button>
        <button
          onClick={() => setActiveTab("ai_suite")}
          className={`px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap transition ${
            activeTab === "ai_suite" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          🤖 Governed AI Intelligence Suite
        </button>
        <button
          onClick={() => setActiveTab("localization")}
          className={`px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap transition ${
            activeTab === "localization" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          🌍 Multi-Country Localization
        </button>
      </div>

      {/* Security Tab */}
      {activeTab === "security" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
            <h3 className="font-semibold text-gray-800 text-sm">Enterprise Password & IAM Policy</h3>
            <div className="space-y-3 text-xs text-gray-700">
              <div className="flex justify-between py-2 border-b">
                <span className="font-medium text-gray-600">Minimum Password Length:</span>
                <span className="font-bold text-indigo-600">{securityPolicy?.min_password_length || 12} characters</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="font-medium text-gray-600">Special Character & Number Required:</span>
                <span className="font-bold text-emerald-600">Enforced</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="font-medium text-gray-600">Session Inactivity Timeout:</span>
                <span className="font-bold text-gray-800">{securityPolicy?.session_timeout_minutes || 60} minutes</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="font-medium text-gray-600">Max Failed Login Lockout:</span>
                <span className="font-bold text-red-600">{securityPolicy?.max_failed_logins || 3} attempts</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="font-medium text-gray-600">IP Whitelisting:</span>
                <span className="font-bold text-indigo-600">
                  {securityPolicy?.ip_whitelist_enabled ? "Active" : "Disabled (Open Access)"}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
            <h3 className="font-semibold text-gray-800 text-sm">Active Sessions & Instant Revocation</h3>
            <div className="space-y-2">
              {(sessions || []).map((s: any) => (
                <div key={s.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200 flex justify-between items-center text-xs">
                  <div>
                    <p className="font-semibold text-gray-900">IP: {s.ip_address || "127.0.0.1"}</p>
                    <p className="text-gray-500 font-mono text-[10px] truncate max-w-[180px]">{s.user_agent}</p>
                  </div>
                  <button
                    onClick={() => handleRevokeSession(s.id)}
                    className="px-2.5 py-1 bg-red-50 hover:bg-red-100 text-red-700 font-semibold rounded border border-red-200 transition"
                  >
                    Kill Session
                  </button>
                </div>
              ))}
              {(!sessions || sessions.length === 0) && (
                <p className="text-xs text-gray-400 py-6 text-center">No active background sessions.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI Suite Tab */}
      {activeTab === "ai_suite" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Predictive Attrition */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-xl">📊</span>
              <div>
                <h3 className="font-semibold text-gray-800 text-sm">AI Attrition Risk Predictor</h3>
                <p className="text-xs text-gray-500">Evaluates attendance, absence spikes, and tenure signals</p>
              </div>
            </div>

            <div className="flex gap-2">
              <select
                value={selectedPersonForAi}
                onChange={(e) => setSelectedPersonForAi(e.target.value)}
                className="flex-1 border rounded-lg px-3 py-2 text-xs text-gray-800"
              >
                <option value="">-- Choose Employee --</option>
                {(candidates || []).map((c: any) => (
                  <option key={c.person_id} value={c.person_id}>
                    {c.person?.full_name || "Employee"} ({c.applied_position || "Team Member"})
                  </option>
                ))}
              </select>
              <button
                onClick={handlePredictAttrition}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs px-4 py-2 rounded-lg font-medium shadow-sm transition"
              >
                Predict Risk
              </button>
            </div>

            {attritionResult && (
              <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-xl space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-gray-800">Risk Assessment:</span>
                  <span
                    className={`px-2.5 py-0.5 rounded font-extrabold ${
                      attritionResult.risk_level === "High"
                        ? "bg-red-100 text-red-800"
                        : "bg-emerald-100 text-emerald-800"
                    }`}
                  >
                    {attritionResult.risk_level} Risk ({attritionResult.risk_score}%)
                  </span>
                </div>
                <div>
                  <p className="font-medium text-gray-700 mb-1">Key Factors Identified:</p>
                  <ul className="list-disc pl-4 text-gray-600 space-y-0.5">
                    {(attritionResult.factors || []).map((f: string, i: number) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="font-medium text-gray-700 mb-1">Recommended Interventions:</p>
                  <ul className="list-disc pl-4 text-indigo-700 space-y-0.5 font-medium">
                    {(attritionResult.recommendations || []).map((r: string, i: number) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* AI HR Helpdesk */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-xl">🤖</span>
              <div>
                <h3 className="font-semibold text-gray-800 text-sm">AI HR Helpdesk Knowledge Search</h3>
                <p className="text-xs text-gray-500">Instant answers to HR policies, leaves, and employee handbooks</p>
              </div>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={helpdeskQuestion}
                onChange={(e) => setHelpdeskQuestion(e.target.value)}
                placeholder="Ask any HR policy question..."
                className="flex-1 border rounded-lg px-3 py-2 text-xs text-gray-800"
              />
              <button
                onClick={handleAskHelpdesk}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs px-4 py-2 rounded-lg font-medium shadow-sm transition"
              >
                Ask Copilot
              </button>
            </div>

            {aiAnswer && (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-gray-800">
                    Category: <span className="uppercase text-indigo-600">{aiAnswer.category || "General"}</span>
                  </span>
                  <span className="text-emerald-700 font-bold">Confidence: {Math.round(aiAnswer.confidence * 100)}%</span>
                </div>
                <p className="text-gray-700 leading-relaxed font-sans">{aiAnswer.answer}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Localization Tab */}
      {activeTab === "localization" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Currency Converter */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
            <h3 className="font-semibold text-gray-800 text-sm">Multi-Currency Global Converter</h3>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <label className="block text-gray-600 mb-1">From Currency</label>
                <input
                  type="text"
                  value={fromCurr}
                  onChange={(e) => setFromCurr(e.target.value.toUpperCase())}
                  className="w-full border rounded px-2.5 py-1.5 font-mono"
                />
              </div>
              <div>
                <label className="block text-gray-600 mb-1">To Currency</label>
                <input
                  type="text"
                  value={toCurr}
                  onChange={(e) => setToCurr(e.target.value.toUpperCase())}
                  className="w-full border rounded px-2.5 py-1.5 font-mono"
                />
              </div>
              <div>
                <label className="block text-gray-600 mb-1">Amount</label>
                <input
                  type="number"
                  value={currAmount}
                  onChange={(e) => setCurrAmount(Number(e.target.value))}
                  className="w-full border rounded px-2.5 py-1.5 font-mono"
                />
              </div>
            </div>
            <button
              onClick={handleConvertCurrency}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold py-2 rounded-lg transition"
            >
              Calculate Live Exchange
            </button>
            {convertedResult && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-mono text-emerald-900">
                {convertedResult.original_amount} {convertedResult.from} ={" "}
                <span className="font-bold text-sm">{convertedResult.converted_amount} {convertedResult.to}</span>{" "}
                (Rate: {convertedResult.rate})
              </div>
            )}
          </div>

          {/* Holiday Calendars */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
            <h3 className="font-semibold text-gray-800 text-sm">Country Holiday Calendars</h3>
            <div className="space-y-2">
              {(calendars || []).map((cal: any) => (
                <div key={cal.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200 flex justify-between items-center text-xs">
                  <div>
                    <h5 className="font-semibold text-gray-900">{cal.name}</h5>
                    <p className="text-gray-500">Year {cal.year} • ISO Country Code: {cal.country_code}</p>
                  </div>
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded font-semibold text-[10px]">
                    {cal.country_code}
                  </span>
                </div>
              ))}
              {(!calendars || calendars.length === 0) && (
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 flex justify-between items-center text-xs">
                  <div>
                    <h5 className="font-semibold text-gray-900">India National 2026</h5>
                    <p className="text-gray-500">Year 2026 • ISO Country Code: IN</p>
                  </div>
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded font-semibold text-[10px]">IN</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
