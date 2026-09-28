"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function AdminKnowledgePage() {
  const [activeTab, setActiveTab] = useState<"articles" | "create" | "reviews" | "categories">("articles");

  // Article creation form
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [articleType, setArticleType] = useState("ARTICLE");
  const [visibility, setVisibility] = useState("ALL_EMPLOYEES");
  const [reviewDueAt, setReviewDueAt] = useState("");
  const [changeSummary, setChangeSummary] = useState("Initial version");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Category creation form
  const [newCatName, setNewCatName] = useState("");
  const [newCatSlug, setNewCatSlug] = useState("");
  const [newCatDesc, setNewCatDesc] = useState("");
  const [newCatParent, setNewCatParent] = useState("");
  const [submittingCat, setSubmittingCat] = useState(false);

  // Queries
  const { data: articles, mutate: mutateArticles } = useSWR("/api/v3/knowledge/articles", fetcher);
  const { data: categories, mutate: mutateCategories } = useSWR("/api/v3/knowledge/categories?tree=true", fetcher);
  const { data: flatCategories } = useSWR("/api/v3/knowledge/categories", fetcher);
  const { data: reviewTasks, mutate: mutateReviews } = useSWR("/api/v3/knowledge/reviews/tasks", fetcher);
  const { data: dashboard } = useSWR("/api/v3/knowledge/dashboard", fetcher);

  const handleCreateArticle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !categoryId || !content) {
      alert("Title, category, and content are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      const generatedSlug = slug || title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
      await api.post("/api/v3/knowledge/articles", {
        category_id: categoryId,
        title,
        slug: generatedSlug,
        summary,
        content_reference: content,
        article_type: articleType,
        visibility,
        review_due_at: reviewDueAt ? new Date(reviewDueAt).toISOString() : null,
        change_summary: changeSummary || "Initial draft",
      });
      setStatusMessage("Knowledge article created successfully!");
      setTitle("");
      setSlug("");
      setSummary("");
      setContent("");
      setReviewDueAt("");
      mutateArticles();
      setActiveTab("articles");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Creation failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await api.post(`/api/v3/knowledge/articles/${id}/publish`);
      mutateArticles();
      setStatusMessage("Article published successfully!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Publish failed");
    }
  };

  const handleArchive = async (id: string) => {
    try {
      await api.post(`/api/v3/knowledge/articles/${id}/archive`);
      mutateArticles();
      setStatusMessage("Article archived.");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Archive failed");
    }
  };

  const handleCompleteReview = async (taskId: string) => {
    try {
      await api.post(`/api/v3/knowledge/reviews/tasks/${taskId}/complete`, {
        action: "CONFIRMED_ACCURATE",
        notes: "Verified article content is accurate and up to date.",
      });
      mutateReviews();
      setStatusMessage("Review task completed!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to complete review task");
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName) return;
    setSubmittingCat(true);
    try {
      const genSlug = newCatSlug || newCatName.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      await api.post("/api/v3/knowledge/categories", {
        name: newCatName,
        slug: genSlug,
        description: newCatDesc,
        parent_id: newCatParent || null,
      });
      setStatusMessage("Category created successfully!");
      setNewCatName("");
      setNewCatSlug("");
      setNewCatDesc("");
      setNewCatParent("");
      mutateCategories();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create category");
    } finally {
      setSubmittingCat(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📖</span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Knowledge Base Administration
            </h1>
          </div>
          <p className="text-slate-500 text-xs mt-1">
            Manage hierarchical categories, author articles, control version history, and fulfill staleness review tasks.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg">
          {(["articles", "create", "reviews", "categories"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition ${
                activeTab === tab
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab === "create" ? "+ New Article" : tab}
            </button>
          ))}
        </div>
      </div>

      {statusMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs p-3 rounded-lg flex items-center justify-between">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="font-bold text-slate-500">×</button>
        </div>
      )}

      {/* Metrics Row */}
      {dashboard && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs font-semibold text-slate-500">Total Articles</p>
            <p className="text-2xl font-extrabold text-slate-900 mt-1">{dashboard.total_articles}</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs font-semibold text-slate-500">Published</p>
            <p className="text-2xl font-extrabold text-emerald-600 mt-1">{dashboard.published_articles}</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs font-semibold text-slate-500">Pending Reviews</p>
            <p className="text-2xl font-extrabold text-amber-600 mt-1">{dashboard.pending_reviews}</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs font-semibold text-slate-500">Helpfulness Score</p>
            <p className="text-2xl font-extrabold text-indigo-600 mt-1">{dashboard.helpfulness_score_pct}%</p>
          </div>
        </div>
      )}

      {/* Articles List Tab */}
      {activeTab === "articles" && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900">Articles Directory</h2>
            <button
              onClick={() => setActiveTab("create")}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
            >
              + Create Article
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {!articles || articles.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">No articles created yet.</div>
            ) : (
              articles.map((art: any) => (
                <div key={art.id} className="p-5 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] bg-slate-100 text-slate-700 font-bold px-2 py-0.5 rounded">
                        v{art.current_version || 1}
                      </span>
                      <span className="text-[10px] bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded uppercase">
                        {art.article_type}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          art.status === "PUBLISHED"
                            ? "bg-emerald-100 text-emerald-800"
                            : art.status === "ARCHIVED"
                            ? "bg-slate-200 text-slate-600"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {art.status}
                      </span>
                      <span className="text-xs text-slate-400">{art.category_name}</span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-900">{art.title}</h3>
                    <p className="text-xs text-slate-500">{art.summary || "No summary"}</p>

                    <div className="flex items-center gap-4 text-[11px] text-slate-400 mt-1">
                      <span>Views: {art.view_count || 0}</span>
                      <span>•</span>
                      <span>Helpful: {art.helpful_count || 0}</span>
                      <span>•</span>
                      <span>Updated: {new Date(art.updated_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {art.status === "DRAFT" && (
                      <button
                        onClick={() => handlePublish(art.id)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                      >
                        Publish
                      </button>
                    )}
                    {art.status !== "ARCHIVED" && (
                      <button
                        onClick={() => handleArchive(art.id)}
                        className="bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-medium px-3 py-1.5 rounded-lg transition"
                      >
                        Archive
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Create Article Tab */}
      {activeTab === "create" && (
        <form onSubmit={handleCreateArticle} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">Create Knowledge Article</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Articles start as drafts and generate immutable version records with audit tracking on each edit.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Article Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Employee Relocation & Expense Policy"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Category *</label>
              <select
                required
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select Category...</option>
                {(flatCategories || []).map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Type</label>
              <select
                value={articleType}
                onChange={(e) => setArticleType(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="ARTICLE">General Article</option>
                <option value="POLICY_GUIDE">Policy Guide</option>
                <option value="SOP">Standard Operating Procedure (SOP)</option>
                <option value="FAQ">FAQ Document</option>
                <option value="RUNBOOK">IT / Operations Runbook</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Visibility</label>
              <select
                value={visibility}
                onChange={(e) => setVisibility(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="ALL_EMPLOYEES">All Company Employees</option>
                <option value="MANAGERS">People Managers Only</option>
                <option value="HR_ONLY">HR & Compliance Admins Only</option>
                <option value="CUSTOM_AUDIENCE">Custom Audience Rules</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Next Review Due Date (Optional)</label>
              <input
                type="date"
                value={reviewDueAt}
                onChange={(e) => setReviewDueAt(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Summary / Teaser</label>
            <input
              type="text"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Executive summary or quick overview..."
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Article Content *</label>
            <textarea
              required
              rows={8}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write the knowledge content here in full..."
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-sans"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Change Summary</label>
            <input
              type="text"
              value={changeSummary}
              onChange={(e) => setChangeSummary(e.target.value)}
              placeholder="e.g. Initial draft creation"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setActiveTab("articles")}
              className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-4 py-2 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-5 py-2 rounded-lg shadow-sm transition"
            >
              {isSubmitting ? "Saving..." : "Save Draft Article"}
            </button>
          </div>
        </form>
      )}

      {/* Review Tasks Queue Tab */}
      {activeTab === "reviews" && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Knowledge Review Governance Queue</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Articles that have reached their scheduled review date must be checked for staleness or regulatory accuracy.
            </p>
          </div>

          <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
            {!reviewTasks || reviewTasks.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                ✓ All knowledge articles are up to date! No pending review tasks.
              </div>
            ) : (
              reviewTasks.map((t: any) => (
                <div key={t.id} className="p-4 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded">
                        {t.status}
                      </span>
                      <span className="text-xs text-slate-500">Due: {new Date(t.due_date).toLocaleDateString()}</span>
                    </div>
                    <p className="text-sm font-bold text-slate-900">Review Article ID: {t.article_id}</p>
                    <p className="text-xs text-slate-500">Reason: {t.review_reason || "Scheduled staleness review"}</p>
                  </div>

                  {t.status === "PENDING" && (
                    <button
                      onClick={() => handleCompleteReview(t.id)}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                    >
                      Mark Reviewed & Accurate
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Categories Management Tab */}
      {activeTab === "categories" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Create Category Form */}
          <form onSubmit={handleCreateCategory} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-slate-900">Create Category</h2>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Category Name *</label>
              <input
                type="text"
                required
                value={newCatName}
                onChange={(e) => setNewCatName(e.target.value)}
                placeholder="e.g. Employee Handbook"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Parent Category (Optional)</label>
              <select
                value={newCatParent}
                onChange={(e) => setNewCatParent(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">None (Top-Level Category)</option>
                {(flatCategories || []).map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Description</label>
              <textarea
                rows={3}
                value={newCatDesc}
                onChange={(e) => setNewCatDesc(e.target.value)}
                placeholder="Brief summary of what articles belong here..."
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={submittingCat}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition"
            >
              {submittingCat ? "Creating..." : "Create Category"}
            </button>
          </form>

          {/* Categories Hierarchy Display */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-slate-900">Category Hierarchy</h2>
            <div className="space-y-2 border border-slate-100 rounded-lg p-3 max-h-96 overflow-y-auto">
              {!categories || categories.length === 0 ? (
                <p className="text-xs text-slate-400">No categories found.</p>
              ) : (
                categories.map((cat: any) => (
                  <div key={cat.id} className="text-xs space-y-1">
                    <p className="font-bold text-slate-800 flex items-center gap-1">
                      <span>📁</span>
                      <span>{cat.name}</span>
                    </p>
                    {cat.children && cat.children.length > 0 && (
                      <div className="pl-6 space-y-1 border-l border-slate-200 ml-2">
                        {cat.children.map((sub: any) => (
                          <p key={sub.id} className="text-slate-600 flex items-center gap-1">
                            <span>📄</span>
                            <span>{sub.name}</span>
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
