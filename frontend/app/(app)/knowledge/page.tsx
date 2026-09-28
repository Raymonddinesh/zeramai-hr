"use client";

import { useState } from "react";
import useSWR from "swr";
import api from "@/lib/api";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export default function KnowledgeHubPage() {
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<"ALL" | "FAQ" | "RUNBOOK" | "ARTICLE">("ALL");
  const [feedbackGiven, setFeedbackGiven] = useState<string | null>(null);

  // Queries
  const { data: categories } = useSWR("/api/v3/knowledge/categories?tree=true", fetcher);
  const { data: articles, mutate: mutateArticles } = useSWR(
    `/api/v3/knowledge/articles${selectedCategoryId ? `?category_id=${selectedCategoryId}` : ""}`,
    fetcher
  );
  const { data: selectedArticle, mutate: mutateSelectedArticle } = useSWR(
    selectedArticleId ? `/api/v3/knowledge/articles/${selectedArticleId}` : null,
    fetcher
  );
  const { data: searchResults } = useSWR(
    searchQuery.trim().length > 1 ? `/api/v3/knowledge/search?q=${encodeURIComponent(searchQuery)}` : null,
    fetcher
  );
  const { data: relatedArticles } = useSWR(
    selectedArticleId ? `/api/v3/knowledge/articles/${selectedArticleId}/related` : null,
    fetcher
  );

  const handleFeedback = async (isHelpful: boolean) => {
    if (!selectedArticleId) return;
    try {
      await api.post(`/api/v3/knowledge/articles/${selectedArticleId}/feedback`, {
        feedback_type: isHelpful ? "HELPFUL" : "NOT_HELPFUL",
      });
      setFeedbackGiven(isHelpful ? "helpful" : "not_helpful");
      mutateSelectedArticle();
      mutateArticles();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Feedback submission failed");
    }
  };

  const displayedArticles = searchQuery.trim().length > 1
    ? (searchResults?.results || [])
    : (articles || []).filter((art: any) => {
        if (activeFilter === "ALL") return true;
        return art.article_type === activeFilter;
      });

  return (
    <div className="space-y-6">
      {/* Header & Search */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-white shadow-sm">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">📚</span>
            <h1 className="text-2xl font-bold tracking-tight">Enterprise Knowledge Hub</h1>
          </div>
          <p className="text-slate-400 text-sm mb-4">
            Curated organizational knowledge, standard operating procedures, policies, and IT troubleshooting guides.
          </p>

          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search across all knowledge articles, FAQs, guides, and runbooks..."
              className="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-4 py-3 pl-11 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
            />
            <span className="absolute left-3.5 top-3.5 text-slate-400">🔍</span>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-3 text-slate-400 hover:text-white text-xs bg-slate-700 px-2 py-1 rounded"
              >
                Clear
              </button>
            )}
          </div>
          {searchQuery.trim().length > 1 && searchResults && (
            <p className="text-xs text-slate-400 mt-2">
              Found {searchResults.total_hits} results for &ldquo;{searchQuery}&rdquo;
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left: Category Navigation */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center justify-between">
              <span>Categories</span>
              <button
                onClick={() => setSelectedCategoryId(null)}
                className={`text-xs ${!selectedCategoryId ? "text-indigo-600 font-bold" : "text-slate-500 hover:text-slate-900"}`}
              >
                All
              </button>
            </h2>

            <div className="space-y-1">
              {(categories || []).map((cat: any) => (
                <div key={cat.id} className="space-y-1">
                  <button
                    onClick={() => {
                      setSelectedCategoryId(cat.id);
                      setSelectedArticleId(null);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition flex items-center justify-between ${
                      selectedCategoryId === cat.id
                        ? "bg-indigo-50 text-indigo-700 font-bold"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span className="truncate">{cat.name}</span>
                    {cat.children && cat.children.length > 0 && (
                      <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full">
                        {cat.children.length}
                      </span>
                    )}
                  </button>
                  {cat.children && cat.children.length > 0 && (
                    <div className="pl-4 space-y-0.5 border-l border-slate-100 ml-2">
                      {cat.children.map((sub: any) => (
                        <button
                          key={sub.id}
                          onClick={() => {
                            setSelectedCategoryId(sub.id);
                            setSelectedArticleId(null);
                          }}
                          className={`w-full text-left px-2 py-1 rounded text-[11px] transition ${
                            selectedCategoryId === sub.id
                              ? "bg-indigo-50 text-indigo-700 font-bold"
                              : "text-slate-600 hover:bg-slate-50"
                          }`}
                        >
                          {sub.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Filter by Type */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Article Type</h3>
            <div className="flex flex-wrap gap-1.5">
              {(["ALL", "ARTICLE", "FAQ", "RUNBOOK"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setActiveFilter(t)}
                  className={`text-xs px-2.5 py-1 rounded-md font-medium transition ${
                    activeFilter === t
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Center / Right: Article Feed or Detailed Reader */}
        <div className="lg:col-span-3">
          {selectedArticle ? (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
              {/* Top Bar */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <button
                  onClick={() => setSelectedArticleId(null)}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                >
                  ← Back to articles list
                </button>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                    v{selectedArticle.current_version || 1}
                  </span>
                  <span className="text-[11px] bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded uppercase font-semibold">
                    {selectedArticle.article_type}
                  </span>
                </div>
              </div>

              {/* Title & Metadata */}
              <div>
                <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-1">
                  {selectedArticle.category_name || "Knowledge"}
                </p>
                <h2 className="text-2xl font-bold text-slate-900">{selectedArticle.title}</h2>
                {selectedArticle.summary && (
                  <p className="text-slate-600 text-sm mt-2 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                    {selectedArticle.summary}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-3">
                  <span>Views: {selectedArticle.view_count || 1}</span>
                  <span>•</span>
                  <span>Helpful: {selectedArticle.helpful_count || 0}</span>
                  <span>•</span>
                  <span>Published: {selectedArticle.published_at ? new Date(selectedArticle.published_at).toLocaleDateString() : "Draft"}</span>
                </div>
              </div>

              {/* Article Content */}
              <div className="prose prose-slate max-w-none border-t border-slate-100 pt-4 text-slate-800 leading-relaxed text-sm whitespace-pre-wrap font-sans">
                {selectedArticle.content_reference || "No content available."}
              </div>

              {/* Helpfulness Feedback */}
              <div className="border-t border-slate-200 pt-4 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50 p-4 rounded-xl">
                <div>
                  <p className="text-sm font-semibold text-slate-900">Was this article helpful?</p>
                  <p className="text-xs text-slate-500">Your feedback improves our knowledge base accuracy.</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleFeedback(true)}
                    disabled={feedbackGiven !== null}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition flex items-center gap-1 ${
                      feedbackGiven === "helpful"
                        ? "bg-emerald-600 text-white border-emerald-600"
                        : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
                    }`}
                  >
                    👍 Yes ({selectedArticle.helpful_count || 0})
                  </button>
                  <button
                    onClick={() => handleFeedback(false)}
                    disabled={feedbackGiven !== null}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition flex items-center gap-1 ${
                      feedbackGiven === "not_helpful"
                        ? "bg-rose-600 text-white border-rose-600"
                        : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
                    }`}
                  >
                    👎 No ({selectedArticle.not_helpful_count || 0})
                  </button>
                </div>
              </div>

              {/* Related Knowledge Articles */}
              {relatedArticles && relatedArticles.length > 0 && (
                <div className="border-t border-slate-100 pt-4">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Related Articles</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {relatedArticles.map((rel: any) => (
                      <button
                        key={rel.id}
                        onClick={() => {
                          setSelectedArticleId(rel.related_article_id);
                          setFeedbackGiven(null);
                        }}
                        className="text-left p-3 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition text-xs"
                      >
                        <p className="font-semibold text-slate-900 truncate">
                          {rel.related_article?.title || "Related Article"}
                        </p>
                        <p className="text-slate-500 text-[11px] mt-0.5 truncate">
                          {rel.relation_type.replace("_", " ")}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {displayedArticles.length === 0 ? (
                <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
                  <p className="text-3xl mb-2">📖</p>
                  <p className="font-semibold text-slate-800">No articles found</p>
                  <p className="text-xs text-slate-400 mt-1">Try another category, filter, or search term.</p>
                </div>
              ) : (
                displayedArticles.map((art: any) => (
                  <div
                    key={art.id}
                    onClick={() => {
                      setSelectedArticleId(art.id);
                      setFeedbackGiven(null);
                    }}
                    className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:border-indigo-300 hover:shadow-md transition cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded uppercase tracking-wider">
                            {art.article_type}
                          </span>
                          {art.category_name && (
                            <span className="text-xs text-slate-500 font-medium">
                              {art.category_name}
                            </span>
                          )}
                        </div>
                        <h3 className="text-base font-bold text-slate-900 hover:text-indigo-600 transition">
                          {art.title}
                        </h3>
                        {art.summary && (
                          <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                            {art.summary}
                          </p>
                        )}
                      </div>
                      <span className="text-slate-300 text-lg shrink-0">→</span>
                    </div>

                    <div className="flex items-center gap-4 text-[11px] text-slate-400 mt-3 pt-3 border-t border-slate-100">
                      <span>v{art.current_version || 1}</span>
                      <span>•</span>
                      <span>{art.view_count || 0} views</span>
                      <span>•</span>
                      <span>{art.helpful_count || 0} helpful</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
