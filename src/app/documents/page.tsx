"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const ML_SERVICE_URL = process.env.NEXT_PUBLIC_ML_SERVICE_URL || "http://localhost:8000";

interface RequirementSummary {
  total: number;
  mandatory: number;
  optional: number;
}

interface TenderRequirement {
  requirement_id: string;
  category: string;
  requirement_text: string;
  classification: string;
  compliance_status: string;
  page_number: number | null;
  source_section: string | null;
  notes: string | null;
}

interface DocumentSummary {
  job_id: string;
  filename: string;
  status: string;
  title: string | null;
  author: string | null;
  document_type: string | null;
  page_count: number | null;
  chunk_count: number | null;
  created_at: string;
  tender_reference: string | null;
  requirements_summary: RequirementSummary | null;
}

interface DocumentDetail {
  job_id: string;
  filename: string;
  status: string;
  created_at: string;
  page_count: number | null;
  chunk_count: number | null;
  content_preview: string | null;
  title: string | null;
  author: string | null;
  summary: string | null;
  document_type: string | null;
  key_topics: string[] | null;
  entities: { name: string; entity_type: string }[] | null;
  language: string | null;
  tender_reference: string | null;
  submission_deadline: string | null;
  estimated_value: string | null;
  requirements_summary: RequirementSummary | null;
  requirements: TenderRequirement[] | null;
}

interface DocumentListResponse {
  documents: DocumentSummary[];
  total: number;
  limit: number;
  offset: number;
}

// Category colors and labels
const categoryStyles: Record<string, { bg: string; text: string; label: string }> = {
  EQUIPMENT_SPECIFICATION: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Equipment" },
  TIMELINE: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Timeline" },
  COMPLIANCE: { bg: "bg-purple-500/20", text: "text-purple-400", label: "Compliance" },
  TECHNICAL: { bg: "bg-cyan-500/20", text: "text-cyan-400", label: "Technical" },
  FINANCIAL: { bg: "bg-green-500/20", text: "text-green-400", label: "Financial" },
  LEGAL: { bg: "bg-red-500/20", text: "text-red-400", label: "Legal" },
  DOCUMENTATION: { bg: "bg-indigo-500/20", text: "text-indigo-400", label: "Documentation" },
  QUALITY: { bg: "bg-pink-500/20", text: "text-pink-400", label: "Quality" },
  SAFETY: { bg: "bg-orange-500/20", text: "text-orange-400", label: "Safety" },
  ENVIRONMENTAL: { bg: "bg-teal-500/20", text: "text-teal-400", label: "Environmental" },
  DELIVERY: { bg: "bg-sky-500/20", text: "text-sky-400", label: "Delivery" },
  WARRANTY: { bg: "bg-lime-500/20", text: "text-lime-400", label: "Warranty" },
  OTHER: { bg: "bg-zinc-500/20", text: "text-zinc-400", label: "Other" },
};

// Compliance status styles
const complianceStyles: Record<string, { bg: string; text: string }> = {
  YES: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
  NO: { bg: "bg-red-500/20", text: "text-red-400" },
  PARTIAL: { bg: "bg-amber-500/20", text: "text-amber-400" },
  UNKNOWN: { bg: "bg-zinc-500/20", text: "text-zinc-400" },
};

// Status badge component
function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    COMPLETED: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    PROCESSING: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    PENDING: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    FAILED: "bg-red-500/20 text-red-400 border-red-500/30",
  };

  const icons: Record<string, string> = {
    COMPLETED: "✓",
    PROCESSING: "⟳",
    PENDING: "◷",
    FAILED: "✕",
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border
        ${styles[status] || styles.PENDING}
      `}
    >
      <span className={status === "PROCESSING" ? "animate-spin" : ""}>{icons[status]}</span>
      {status}
    </span>
  );
}

// Document type icon
function DocTypeIcon({ type }: { type: string | null }) {
  const icons: Record<string, string> = {
    TENDER: "📋",
    RFP: "📝",
    RFQ: "💰",
    CONTRACT: "📜",
    SPECIFICATION: "📑",
    TECHNICAL_DOCUMENT: "⚙️",
    REPORT: "📊",
    ARTICLE: "📰",
    MANUAL: "📖",
    RESEARCH_PAPER: "🔬",
    PRESENTATION: "📽️",
    OTHER: "📄",
  };
  return <span className="text-2xl">{icons[type || "OTHER"] || "📄"}</span>;
}

// Requirements summary badge
function RequirementsBadge({ summary }: { summary: RequirementSummary | null }) {
  if (!summary || summary.total === 0) return null;

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/20 text-purple-400 rounded-full text-xs font-medium border border-purple-500/30">
      📋 {summary.total} reqs
      <span className="opacity-60">
        ({summary.mandatory}M / {summary.optional}O)
      </span>
    </span>
  );
}

// Category badge
function CategoryBadge({ category }: { category: string }) {
  const style = categoryStyles[category] || categoryStyles.OTHER;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

// Requirements table component
function RequirementsTable({
  requirements,
  onCategoryFilter,
  categoryFilter,
}: {
  requirements: TenderRequirement[];
  onCategoryFilter: (category: string | null) => void;
  categoryFilter: string | null;
}) {
  // Get unique categories
  const categories = [...new Set(requirements.map((r) => r.category))].sort();

  // Filter requirements
  const filteredRequirements = categoryFilter
    ? requirements.filter((r) => r.category === categoryFilter)
    : requirements;

  return (
    <div className="space-y-4">
      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onCategoryFilter(null)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            !categoryFilter
              ? "bg-amber-500 text-zinc-900"
              : "bg-zinc-700/50 text-zinc-300 hover:bg-zinc-700"
          }`}
        >
          All ({requirements.length})
        </button>
        {categories.map((cat) => {
          const count = requirements.filter((r) => r.category === cat).length;
          const style = categoryStyles[cat] || categoryStyles.OTHER;
          return (
            <button
              key={cat}
              onClick={() => onCategoryFilter(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                categoryFilter === cat
                  ? "bg-amber-500 text-zinc-900"
                  : `${style.bg} ${style.text} hover:opacity-80`
              }`}
            >
              {style.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Requirements list */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
        {filteredRequirements.map((req, idx) => (
          <div
            key={req.requirement_id || idx}
            className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-700/50"
          >
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-500 font-mono">{req.requirement_id}</span>
                <CategoryBadge category={req.category} />
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    req.classification === "MANDATORY"
                      ? "bg-red-500/20 text-red-400"
                      : "bg-zinc-500/20 text-zinc-400"
                  }`}
                >
                  {req.classification}
                </span>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  complianceStyles[req.compliance_status]?.bg || "bg-zinc-500/20"
                } ${complianceStyles[req.compliance_status]?.text || "text-zinc-400"}`}
              >
                {req.compliance_status}
              </span>
            </div>
            <p className="text-sm text-zinc-200 leading-relaxed">{req.requirement_text}</p>
            <div className="flex flex-wrap gap-3 mt-2">
              {req.page_number && (
                <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                  📄 Page {req.page_number}
                </span>
              )}
              {req.source_section && (
                <span className="text-xs text-zinc-400">📍 Section: {req.source_section}</span>
              )}
            </div>
            {req.notes && <p className="text-xs text-zinc-400 mt-1 italic">💡 {req.notes}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

// Document card component
function DocumentCard({
  doc,
  isExpanded,
  onToggle,
  detail,
  isLoading,
}: {
  doc: DocumentSummary;
  isExpanded: boolean;
  onToggle: () => void;
  detail: DocumentDetail | null;
  isLoading: boolean;
}) {
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"info" | "requirements">("info");

  const formattedDate = new Date(doc.created_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={`
        bg-zinc-800/50 rounded-2xl border transition-all duration-300 overflow-hidden
        ${isExpanded ? "border-amber-500/50" : "border-zinc-700/50 hover:border-zinc-600"}
      `}
    >
      {/* Card Header - Always Visible */}
      <button
        onClick={onToggle}
        className="w-full p-5 flex items-start gap-4 text-left hover:bg-zinc-700/20 transition-colors"
      >
        <div className="flex-shrink-0 mt-1">
          <DocTypeIcon type={doc.document_type} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="font-semibold text-white truncate">
                {doc.title || doc.filename}
              </h3>
              {doc.title && (
                <p className="text-sm text-zinc-400 truncate">{doc.filename}</p>
              )}
              {doc.tender_reference && (
                <p className="text-xs text-amber-400 mt-1">Ref: {doc.tender_reference}</p>
              )}
            </div>
            <StatusBadge status={doc.status} />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-zinc-400">
            {doc.author && (
              <span className="flex items-center gap-1.5">
                <span className="text-zinc-500">👤</span>
                {doc.author}
              </span>
            )}
            {doc.page_count && (
              <span className="flex items-center gap-1.5">
                <span className="text-zinc-500">📄</span>
                {doc.page_count} pages
              </span>
            )}
            {doc.chunk_count && (
              <span className="flex items-center gap-1.5">
                <span className="text-zinc-500">🧩</span>
                {doc.chunk_count} chunks
              </span>
            )}
            <span className="flex items-center gap-1.5">
              <span className="text-zinc-500">🕐</span>
              {formattedDate}
            </span>
            <RequirementsBadge summary={doc.requirements_summary} />
          </div>
        </div>

        <div
          className={`
            flex-shrink-0 w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center
            transition-transform duration-300
            ${isExpanded ? "rotate-180" : ""}
          `}
        >
          <span className="text-zinc-300">▼</span>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-5 pb-5 border-t border-zinc-700/50">
          {isLoading ? (
            <div className="py-8 flex items-center justify-center">
              <div className="animate-spin text-2xl">⚙️</div>
              <span className="ml-3 text-zinc-400">Loading details...</span>
            </div>
          ) : detail ? (
            <div className="pt-5 space-y-5">
              {/* Tabs for documents with requirements */}
              {detail.requirements && detail.requirements.length > 0 && (
                <div className="flex gap-2 border-b border-zinc-700 pb-3">
                  <button
                    onClick={() => setActiveTab("info")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      activeTab === "info"
                        ? "bg-amber-500 text-zinc-900"
                        : "bg-zinc-700/50 text-zinc-300 hover:bg-zinc-700"
                    }`}
                  >
                    📄 Document Info
                  </button>
                  <button
                    onClick={() => setActiveTab("requirements")}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      activeTab === "requirements"
                        ? "bg-amber-500 text-zinc-900"
                        : "bg-zinc-700/50 text-zinc-300 hover:bg-zinc-700"
                    }`}
                  >
                    📋 Requirements ({detail.requirements.length})
                  </button>
                </div>
              )}

              {activeTab === "info" ? (
                <>
                  {/* Tender Info */}
                  {(detail.tender_reference ||
                    detail.submission_deadline ||
                    detail.estimated_value) && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {detail.tender_reference && (
                        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
                          <p className="text-xs text-amber-400/70 mb-1">Tender Reference</p>
                          <p className="text-sm text-amber-400 font-medium">
                            {detail.tender_reference}
                          </p>
                        </div>
                      )}
                      {detail.submission_deadline && (
                        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                          <p className="text-xs text-red-400/70 mb-1">Submission Deadline</p>
                          <p className="text-sm text-red-400 font-medium">
                            {detail.submission_deadline}
                          </p>
                        </div>
                      )}
                      {detail.estimated_value && (
                        <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3">
                          <p className="text-xs text-green-400/70 mb-1">Estimated Value</p>
                          <p className="text-sm text-green-400 font-medium">
                            {detail.estimated_value}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Requirements Summary */}
                  {detail.requirements_summary && detail.requirements_summary.total > 0 && (
                    <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4">
                      <h4 className="text-sm font-medium text-purple-400 mb-3">
                        📋 Requirements Summary
                      </h4>
                      <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                          <p className="text-2xl font-bold text-white">
                            {detail.requirements_summary.total}
                          </p>
                          <p className="text-xs text-zinc-400">Total</p>
                        </div>
                        <div className="text-center">
                          <p className="text-2xl font-bold text-red-400">
                            {detail.requirements_summary.mandatory}
                          </p>
                          <p className="text-xs text-zinc-400">Mandatory</p>
                        </div>
                        <div className="text-center">
                          <p className="text-2xl font-bold text-zinc-400">
                            {detail.requirements_summary.optional}
                          </p>
                          <p className="text-xs text-zinc-400">Optional</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Summary */}
                  {detail.summary && (
                    <div>
                      <h4 className="text-sm font-medium text-zinc-400 mb-2">Summary</h4>
                      <p className="text-zinc-200 leading-relaxed">{detail.summary}</p>
                    </div>
                  )}

                  {/* Key Topics */}
                  {detail.key_topics && detail.key_topics.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-zinc-400 mb-2">Key Topics</h4>
                      <div className="flex flex-wrap gap-2">
                        {detail.key_topics.map((topic, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1.5 bg-amber-500/10 text-amber-400 rounded-lg text-sm border border-amber-500/20"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Entities */}
                  {detail.entities && detail.entities.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-zinc-400 mb-2">
                        Extracted Entities
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {detail.entities.map((entity, idx) => (
                          <span
                            key={idx}
                            className={`
                              px-3 py-1.5 rounded-lg text-sm border
                              ${entity.entity_type === "PERSON" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : ""}
                              ${entity.entity_type === "ORGANIZATION" ? "bg-purple-500/10 text-purple-400 border-purple-500/20" : ""}
                              ${entity.entity_type === "LOCATION" ? "bg-green-500/10 text-green-400 border-green-500/20" : ""}
                              ${entity.entity_type === "DATE" ? "bg-orange-500/10 text-orange-400 border-orange-500/20" : ""}
                              ${!["PERSON", "ORGANIZATION", "LOCATION", "DATE"].includes(entity.entity_type) ? "bg-zinc-700/50 text-zinc-300 border-zinc-600/50" : ""}
                            `}
                          >
                            <span className="opacity-60 text-xs mr-1">{entity.entity_type}:</span>
                            {entity.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Content Preview */}
                  {detail.content_preview && (
                    <div>
                      <h4 className="text-sm font-medium text-zinc-400 mb-2">Content Preview</h4>
                      <p className="text-sm text-zinc-400 bg-zinc-900/50 rounded-xl p-4 font-mono leading-relaxed">
                        {detail.content_preview}
                      </p>
                    </div>
                  )}

                  {/* Metadata Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {detail.document_type && (
                      <div className="bg-zinc-900/50 rounded-xl p-3">
                        <p className="text-xs text-zinc-500 mb-1">Type</p>
                        <p className="text-sm text-white font-medium">{detail.document_type}</p>
                      </div>
                    )}
                    {detail.language && (
                      <div className="bg-zinc-900/50 rounded-xl p-3">
                        <p className="text-xs text-zinc-500 mb-1">Language</p>
                        <p className="text-sm text-white font-medium uppercase">
                          {detail.language}
                        </p>
                      </div>
                    )}
                    {detail.page_count && (
                      <div className="bg-zinc-900/50 rounded-xl p-3">
                        <p className="text-xs text-zinc-500 mb-1">Pages</p>
                        <p className="text-sm text-white font-medium">{detail.page_count}</p>
                      </div>
                    )}
                    {detail.chunk_count && (
                      <div className="bg-zinc-900/50 rounded-xl p-3">
                        <p className="text-xs text-zinc-500 mb-1">Chunks</p>
                        <p className="text-sm text-white font-medium">{detail.chunk_count}</p>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                /* Requirements Tab */
                detail.requirements && (
                  <RequirementsTable
                    requirements={detail.requirements}
                    onCategoryFilter={setCategoryFilter}
                    categoryFilter={categoryFilter}
                  />
                )
              )}
            </div>
          ) : (
            <div className="py-8 text-center text-zinc-500">
              Failed to load document details
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Filter tabs
function FilterTabs({
  selected,
  onChange,
  counts,
}: {
  selected: string | null;
  onChange: (status: string | null) => void;
  counts: Record<string, number>;
}) {
  const tabs = [
    { value: null, label: "All", icon: "📚" },
    { value: "COMPLETED", label: "Completed", icon: "✅" },
    { value: "PROCESSING", label: "Processing", icon: "⏳" },
    { value: "FAILED", label: "Failed", icon: "❌" },
  ];

  return (
    <div className="flex gap-2 flex-wrap">
      {tabs.map((tab) => (
        <button
          key={tab.value || "all"}
          onClick={() => onChange(tab.value)}
          className={`
            px-4 py-2 rounded-xl text-sm font-medium transition-all
            ${selected === tab.value
              ? "bg-amber-500 text-zinc-900"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
            }
          `}
        >
          <span className="mr-2">{tab.icon}</span>
          {tab.label}
          {counts[tab.value || "all"] !== undefined && (
            <span className="ml-2 opacity-70">({counts[tab.value || "all"]})</span>
          )}
        </button>
      ))}
    </div>
  );
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [documentDetails, setDocumentDetails] = useState<Record<string, DocumentDetail>>({});
  const [loadingDetail, setLoadingDetail] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Export requirements to CSV
  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const response = await fetch(`${ML_SERVICE_URL}/api/v1/documents/export/requirements/csv`);
      if (!response.ok) throw new Error("Export failed");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = response.headers.get("Content-Disposition")?.split("filename=")[1] || "requirements.csv";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      console.error("Export failed:", e);
      setError("Failed to export requirements");
    } finally {
      setExporting(false);
      setShowExportMenu(false);
    }
  };

  // Export requirements to JSON
  const handleExportJSON = async () => {
    setExporting(true);
    try {
      const response = await fetch(`${ML_SERVICE_URL}/api/v1/documents/export/requirements/json`);
      if (!response.ok) throw new Error("Export failed");
      
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `requirements_export_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      console.error("Export failed:", e);
      setError("Failed to export requirements");
    } finally {
      setExporting(false);
      setShowExportMenu(false);
    }
  };

  // Fetch documents
  useEffect(() => {
    const fetchDocuments = async () => {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        params.set("limit", "50");
        if (statusFilter) {
          params.set("status", statusFilter);
        }

        const response = await fetch(
          `${ML_SERVICE_URL}/api/v1/documents?${params.toString()}`
        );

        if (!response.ok) {
          throw new Error("Failed to fetch documents");
        }

        const data: DocumentListResponse = await response.json();
        setDocuments(data.documents);
        setTotal(data.total);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load documents");
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, [statusFilter]);

  // Fetch document detail when expanded
  const handleToggle = async (jobId: string) => {
    if (expandedId === jobId) {
      setExpandedId(null);
      return;
    }

    setExpandedId(jobId);

    // Check if we already have the details
    if (documentDetails[jobId]) {
      return;
    }

    // Fetch details with requirements
    setLoadingDetail(jobId);
    try {
      const response = await fetch(
        `${ML_SERVICE_URL}/api/v1/documents/${jobId}?include_requirements=true`
      );
      if (response.ok) {
        const detail = await response.json();
        setDocumentDetails((prev) => ({ ...prev, [jobId]: detail }));
      }
    } catch (e) {
      console.error("Failed to fetch document detail:", e);
    } finally {
      setLoadingDetail(null);
    }
  };

  // Calculate counts for filter tabs
  const counts = {
    all: total,
    COMPLETED: documents.filter((d) => d.status === "COMPLETED").length,
    PROCESSING: documents.filter((d) => d.status === "PROCESSING").length,
    FAILED: documents.filter((d) => d.status === "FAILED").length,
  };

  // Calculate total requirements across all documents
  const totalRequirements = documents.reduce(
    (sum, doc) => sum + (doc.requirements_summary?.total || 0),
    0
  );

  return (
    <div className="min-h-screen bg-zinc-900 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 sticky top-0 bg-zinc-900/95 backdrop-blur-sm z-10">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">
                <span className="text-amber-500">📚</span> Tender Document Library
              </h1>
              <p className="text-zinc-400 text-sm mt-1">
                {total} documents • {totalRequirements} total requirements
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Export Dropdown */}
              {totalRequirements > 0 && (
                <div className="relative">
                  <button
                    onClick={() => setShowExportMenu(!showExportMenu)}
                    disabled={exporting}
                    className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white font-medium rounded-xl transition-colors flex items-center gap-2 disabled:opacity-50"
                  >
                    {exporting ? (
                      <>
                        <span className="animate-spin">⏳</span>
                        Exporting...
                      </>
                    ) : (
                      <>
                        📥 Export
                        <span className="text-xs opacity-60">▼</span>
                      </>
                    )}
                  </button>
                  
                  {showExportMenu && !exporting && (
                    <div className="absolute right-0 mt-2 w-48 bg-zinc-800 border border-zinc-700 rounded-xl shadow-xl overflow-hidden z-20">
                      <button
                        onClick={handleExportCSV}
                        className="w-full px-4 py-3 text-left hover:bg-zinc-700 transition-colors flex items-center gap-2"
                      >
                        <span>📊</span>
                        <span>Export as CSV</span>
                      </button>
                      <button
                        onClick={handleExportJSON}
                        className="w-full px-4 py-3 text-left hover:bg-zinc-700 transition-colors flex items-center gap-2 border-t border-zinc-700"
                      >
                        <span>📋</span>
                        <span>Export as JSON</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
              
              <Link
                href="/ingest"
                className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-zinc-900 font-medium rounded-xl transition-colors"
              >
                + Upload New
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Filters */}
        <div className="mb-6">
          <FilterTabs selected={statusFilter} onChange={setStatusFilter} counts={counts} />
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-xl mb-6">
            <p className="font-medium">Error loading documents</p>
            <p className="text-sm opacity-80">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin text-4xl">⚙️</div>
            <span className="ml-4 text-zinc-400 text-lg">Loading documents...</span>
          </div>
        ) : documents.length === 0 ? (
          /* Empty State */
          <div className="text-center py-20">
            <div className="text-6xl mb-4">📭</div>
            <h2 className="text-xl font-semibold text-white mb-2">No tender documents yet</h2>
            <p className="text-zinc-400 mb-6">
              Upload your first tender PDF to automatically extract requirements.
            </p>
            <Link
              href="/ingest"
              className="inline-block px-6 py-3 bg-amber-500 hover:bg-amber-400 text-zinc-900 font-bold rounded-xl transition-colors"
            >
              Upload Tender PDF
            </Link>
          </div>
        ) : (
          /* Document List */
          <div className="space-y-4">
            {documents.map((doc) => (
              <DocumentCard
                key={doc.job_id}
                doc={doc}
                isExpanded={expandedId === doc.job_id}
                onToggle={() => handleToggle(doc.job_id)}
                detail={documentDetails[doc.job_id] || null}
                isLoading={loadingDetail === doc.job_id}
              />
            ))}
          </div>
        )}
      </main>

      {/* Footer Navigation */}
      <footer className="border-t border-zinc-800 mt-12">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <div className="flex justify-center gap-6 text-sm text-zinc-400">
            <Link href="/" className="hover:text-white transition-colors">
              Home
            </Link>
            <Link href="/ingest" className="hover:text-white transition-colors">
              Upload
            </Link>
            <Link href="/documents" className="text-amber-500">
              Documents
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
