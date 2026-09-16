"use client";

import { useRef, useState } from "react";
import axios from "axios";
import { documentsApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function DocumentsPage() {
  const { user } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [personId, setPersonId] = useState("");
  const [docType, setDocType] = useState("resume");
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState("");

  const canUploadAny = user?.role === "super_admin" || user?.role === "hr_admin";

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("person_id", personId);
    fd.append("document_type", docType);
    setUploading(true);
    setMsg("");
    try {
      await documentsApi.upload(fd);
      setMsg("✅ Document uploaded successfully");
      if (fileRef.current) fileRef.current.value = "";
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setMsg("❌ " + (err.response?.data?.detail ?? "Upload failed"));
      } else {
        setMsg("❌ Upload failed");
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (id: string, name: string) => {
    try {
      const res = await documentsApi.download(id);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
    } catch {
      alert("Download failed or access denied.");
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Documents</h2>

      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h3 className="font-semibold text-gray-700 mb-4">Upload Document</h3>
        {msg && <p className="text-sm mb-3">{msg}</p>}
        <form onSubmit={handleUpload} className="space-y-3">
          {canUploadAny && (
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">Person ID</label>
              <input
                type="text"
                required
                value={personId}
                onChange={(e) => setPersonId(e.target.value)}
                placeholder="Paste person UUID"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Document Type</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {["resume","pan","aadhaar","bank_proof","address_proof","offer_letter","nda","certificate"].map((t) => (
                <option key={t} value={t}>{t.replace(/_/g," ")}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">File</label>
            <input ref={fileRef} type="file" required className="text-sm" accept=".pdf,.jpg,.jpeg,.png" />
          </div>
          <button
            type="submit"
            disabled={uploading}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <p className="text-gray-500 text-sm">
          To download a document, paste its document ID below:
        </p>
        <div className="flex gap-3 mt-3">
          <input
            id="dl-id"
            type="text"
            placeholder="Document ID"
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <button
            onClick={() => {
              const id = (document.getElementById("dl-id") as HTMLInputElement).value;
              if (id) handleDownload(id, "document");
            }}
            className="bg-gray-700 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800"
          >
            Download
          </button>
        </div>
      </div>
    </div>
  );
}
