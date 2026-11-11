import React, { useState, useEffect, useRef } from 'react';
import {
  GitCompare,
  Upload,
  FileText,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  MinusCircle,
  RefreshCw,
  Download,
  Printer,
  Eye,
  Sliders,
  ShieldAlert,
  Scale,
  Sparkles,
  ChevronDown
} from 'lucide-react';
import { DocumentMetadata, DocumentComparisonResult } from '../types';
import { api } from '../services/api';
import { DocumentViewerModal } from '../components/DocumentViewerModal';

export const DocumentCompare: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);

  const [doc1Id, setDoc1Id] = useState<string>('');
  const [doc2Id, setDoc2Id] = useState<string>('');

  const [isComparing, setIsComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<DocumentComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // File upload state for Doc A and Doc B
  const [isUploadingA, setIsUploadingA] = useState(false);
  const [isUploadingB, setIsUploadingB] = useState(false);
  const fileInputARef = useRef<HTMLInputElement>(null);
  const fileInputBRef = useRef<HTMLInputElement>(null);

  // Document Viewer Modal
  const [viewerDoc, setViewerDoc] = useState<{ id: string; name: string } | null>(null);

  // Active filter tab for the results
  const [activeTab, setActiveTab] = useState<'matrix' | 'rules' | 'diff' | 'risk'>('matrix');

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setIsLoadingDocs(true);
      const res = await api.listDocuments();
      setDocuments(res.documents);
      if (res.documents.length >= 2) {
        setDoc1Id(res.documents[0].document_id);
        setDoc2Id(res.documents[1].document_id);
      } else if (res.documents.length === 1) {
        setDoc1Id(res.documents[0].document_id);
      }
    } catch (err: any) {
      console.error('Failed to load documents:', err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const handleFileUpload = async (file: File, target: 'A' | 'B') => {
    try {
      if (target === 'A') setIsUploadingA(true);
      else setIsUploadingB(true);

      const res = await api.uploadDocument(file);
      await loadDocuments();

      if (target === 'A') {
        setDoc1Id(res.document.document_id);
      } else {
        setDoc2Id(res.document.document_id);
      }
    } catch (err: any) {
      setError(`Failed to upload ${file.name}: ${err.message || 'Unknown error'}`);
    } finally {
      if (target === 'A') setIsUploadingA(false);
      else setIsUploadingB(false);
    }
  };

  const handleCompare = async () => {
    if (!doc1Id || !doc2Id) {
      setError('Please choose or upload both Baseline (Doc A) and Revision (Doc B) to compare.');
      return;
    }
    if (doc1Id === doc2Id) {
      setError('Please choose two different documents to perform a comparative diff.');
      return;
    }

    try {
      setIsComparing(true);
      setError(null);
      const res = await api.compareDocuments(doc1Id, doc2Id);
      setComparisonResult(res.data);
    } catch (err: any) {
      setError(err.message || 'Comparison analysis failed. Please try again.');
    } finally {
      setIsComparing(false);
    }
  };

  const exportMarkdown = () => {
    if (!comparisonResult) return;
    const md = `# Document Comparison Matrix & Diff Report
**Baseline Document (A):** ${comparisonResult.doc_a_name}
**Revised Document (B):** ${comparisonResult.doc_b_name}
**Generated At:** ${new Date().toLocaleString()}

---

## 1. Executive Summary
${comparisonResult.executive_summary}

---

## 2. Comparative Matrix
| Dimension | ${comparisonResult.doc_a_name} | ${comparisonResult.doc_b_name} | Key Difference & Shift |
|---|---|---|---|
${comparisonResult.comparison_matrix.map(m => `| ${m.dimension} | ${m.doc_a} | ${m.doc_b} | ${m.difference} |`).join('\n')}

---

## 3. Modified Clauses & Rule Liabilities
| Clause / Rule | Baseline (Doc A) | Revised (Doc B) | Liability / Rule Impact |
|---|---|---|---|
${comparisonResult.conflicts_or_changes?.map(c => `| ${c.clause} | ${c.doc_a_version} | ${c.doc_b_version} | ${c.impact} |`).join('\n') || 'None recorded'}

---

## 4. Added Clauses (New in ${comparisonResult.doc_b_name})
${comparisonResult.added_clauses.map(c => `- ${c}`).join('\n')}

---

## 5. Removed Clauses (Deleted from ${comparisonResult.doc_a_name})
${comparisonResult.removed_clauses.map(c => `- ${c}`).join('\n')}

---

## 6. Risk & Compliance Assessment
${comparisonResult.risk_assessment}
`;

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Diff_${comparisonResult.doc_a_name}_vs_${comparisonResult.doc_b_name}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getDoc = (id: string) => documents.find(d => d.document_id === id);
  const docA = getDoc(doc1Id);
  const docB = getDoc(doc2Id);

  const getImpactBadgeClass = (impactStr: string) => {
    const lower = impactStr.toLowerCase();
    if (lower.startsWith('high') || lower.includes('critical') || lower.includes('strict')) {
      return 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-900';
    }
    if (lower.startsWith('med') || lower.includes('moderate')) {
      return 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-900';
    }
    return 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900';
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Module Title Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white p-8 shadow-xl">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-200 text-xs font-semibold mb-3">
            <GitCompare className="w-3.5 h-3.5" />
            <span>Side-by-Side Diff & Audit Matrix</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-2">
            Document Diff & Rule Liability Matrix
          </h2>
          <p className="text-sm md:text-base text-indigo-100/80 leading-relaxed">
            Compare two versions of policies, contracts, agreements, or specifications (e.g., <em>Policy_2024.pdf</em> vs <em>Policy_2025.pdf</em>).
            Our neural agent extracts precise clause additions, deletions, and operational liability changes.
          </p>
        </div>
        <div className="absolute right-0 top-0 bottom-0 w-96 bg-gradient-to-l from-indigo-500/10 to-transparent pointer-events-none" />
      </div>

      {/* Selectors & Upload Workspace */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">
        {/* Document A (Baseline) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <span className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-bold text-xs flex items-center justify-center">
                  A
                </span>
                <div>
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                    Baseline Document (Prior Version)
                  </h3>
                  <p className="text-xs text-slate-500">e.g. Policy_2024.pdf or Original Agreement</p>
                </div>
              </div>
              {docA && (
                <button
                  onClick={() => setViewerDoc({ id: docA.document_id, name: docA.filename })}
                  className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                >
                  <Eye className="w-3.5 h-3.5" /> Preview
                </button>
              )}
            </div>

            {/* Select existing */}
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Select from Indexed Library
              </label>
              <select
                value={doc1Id}
                onChange={(e) => setDoc1Id(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">-- Choose Baseline Document --</option>
                {documents.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.filename} ({d.total_pages} pages, {d.total_chunks} chunks)
                  </option>
                ))}
              </select>

              <div className="flex items-center gap-2 my-3">
                <div className="flex-1 border-t border-slate-200 dark:border-slate-800" />
                <span className="text-xs text-slate-400 font-medium uppercase">or upload new version</span>
                <div className="flex-1 border-t border-slate-200 dark:border-slate-800" />
              </div>

              {/* Direct Upload button */}
              <input
                ref={fileInputARef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt,.md"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFileUpload(e.target.files[0], 'A');
                }}
              />
              <button
                type="button"
                onClick={() => fileInputARef.current?.click()}
                disabled={isUploadingA}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border-2 border-dashed border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/20 text-indigo-700 dark:text-indigo-300 text-xs font-semibold hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition disabled:opacity-50"
              >
                <Upload className="w-4 h-4" />
                <span>{isUploadingA ? 'Uploading & Indexing Baseline...' : 'Upload Baseline File (.pdf, .docx, .xlsx)'}</span>
              </button>
            </div>
          </div>

          {docA && (
            <div className="mt-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/60 flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
              <span className="font-medium truncate max-w-[200px]">{docA.filename}</span>
              <span className="text-slate-400">{docA.total_pages} pages • {docA.total_chunks} chunks</span>
            </div>
          )}
        </div>

        {/* Document B (Revision) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <span className="w-7 h-7 rounded-lg bg-violet-100 dark:bg-violet-950 text-violet-600 dark:text-violet-400 font-bold text-xs flex items-center justify-center">
                  B
                </span>
                <div>
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                    Revision Document (New Version)
                  </h3>
                  <p className="text-xs text-slate-500">e.g. Policy_2025.pdf or Revised Contract</p>
                </div>
              </div>
              {docB && (
                <button
                  onClick={() => setViewerDoc({ id: docB.document_id, name: docB.filename })}
                  className="flex items-center gap-1 text-xs text-violet-600 dark:text-violet-400 hover:underline font-medium"
                >
                  <Eye className="w-3.5 h-3.5" /> Preview
                </button>
              )}
            </div>

            {/* Select existing */}
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                Select from Indexed Library
              </label>
              <select
                value={doc2Id}
                onChange={(e) => setDoc2Id(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                <option value="">-- Choose Revision Document --</option>
                {documents.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.filename} ({d.total_pages} pages, {d.total_chunks} chunks)
                  </option>
                ))}
              </select>

              <div className="flex items-center gap-2 my-3">
                <div className="flex-1 border-t border-slate-200 dark:border-slate-800" />
                <span className="text-xs text-slate-400 font-medium uppercase">or upload new version</span>
                <div className="flex-1 border-t border-slate-200 dark:border-slate-800" />
              </div>

              {/* Direct Upload button */}
              <input
                ref={fileInputBRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt,.md"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFileUpload(e.target.files[0], 'B');
                }}
              />
              <button
                type="button"
                onClick={() => fileInputBRef.current?.click()}
                disabled={isUploadingB}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border-2 border-dashed border-violet-200 dark:border-violet-900/60 bg-violet-50/50 dark:bg-violet-950/20 text-violet-700 dark:text-violet-300 text-xs font-semibold hover:bg-violet-50 dark:hover:bg-violet-950/40 transition disabled:opacity-50"
              >
                <Upload className="w-4 h-4" />
                <span>{isUploadingB ? 'Uploading & Indexing Revision...' : 'Upload Revision File (.pdf, .docx, .xlsx)'}</span>
              </button>
            </div>
          </div>

          {docB && (
            <div className="mt-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/60 flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
              <span className="font-medium truncate max-w-[200px]">{docB.filename}</span>
              <span className="text-slate-400">{docB.total_pages} pages • {docB.total_chunks} chunks</span>
            </div>
          )}
        </div>
      </div>

      {/* Action Button & Errors */}
      <div className="flex flex-col items-center gap-3">
        {error && (
          <div className="max-w-xl w-full p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 rounded-xl border border-red-200 dark:border-red-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          onClick={handleCompare}
          disabled={isComparing || !doc1Id || !doc2Id}
          className="flex items-center gap-3 px-8 py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white font-semibold text-sm shadow-lg shadow-indigo-500/25 disabled:opacity-50 transition transform active:scale-95"
        >
          {isComparing ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Analyzing Comparative Matrix & Risk Shifts...</span>
            </>
          ) : (
            <>
              <GitCompare className="w-4 h-4" />
              <span>Generate Side-by-Side Comparison Matrix</span>
            </>
          )}
        </button>
      </div>

      {/* Comparison Results Area */}
      {comparisonResult && (
        <div className="space-y-6 pt-4 animate-in fade-in duration-300">
          {/* Executive Overview & Quick KPI Cards */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-5">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  Diff Analysis Complete
                </span>
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mt-1">
                  {comparisonResult.doc_a_name} <span className="text-slate-400 font-normal">vs</span> {comparisonResult.doc_b_name}
                </h3>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={exportMarkdown}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                >
                  <Download className="w-3.5 h-3.5" /> Export MD
                </button>
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                >
                  <Printer className="w-3.5 h-3.5" /> Print / PDF
                </button>
              </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200/60 dark:border-emerald-900/40">
                <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 text-xs font-semibold mb-1">
                  <CheckCircle2 className="w-4 h-4" /> Added Clauses
                </div>
                <div className="text-2xl font-bold text-emerald-800 dark:text-emerald-300">
                  {comparisonResult.added_clauses?.length || 0}
                </div>
                <p className="text-[11px] text-emerald-600/80 dark:text-emerald-400/70 mt-0.5">
                  New rules introduced in B
                </p>
              </div>

              <div className="p-4 rounded-xl bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200/60 dark:border-rose-900/40">
                <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 text-xs font-semibold mb-1">
                  <MinusCircle className="w-4 h-4" /> Removed Clauses
                </div>
                <div className="text-2xl font-bold text-rose-800 dark:text-rose-300">
                  {comparisonResult.removed_clauses?.length || 0}
                </div>
                <p className="text-[11px] text-rose-600/80 dark:text-rose-400/70 mt-0.5">
                  Clauses deleted from A
                </p>
              </div>

              <div className="p-4 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40">
                <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 text-xs font-semibold mb-1">
                  <Scale className="w-4 h-4" /> Liability Shifts
                </div>
                <div className="text-2xl font-bold text-amber-800 dark:text-amber-300">
                  {comparisonResult.conflicts_or_changes?.length || 0}
                </div>
                <p className="text-[11px] text-amber-600/80 dark:text-amber-400/70 mt-0.5">
                  Rules or liabilities altered
                </p>
              </div>

              <div className="p-4 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/20 border border-indigo-200/60 dark:border-indigo-900/40">
                <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-400 text-xs font-semibold mb-1">
                  <Sparkles className="w-4 h-4" /> Audit Dimensions
                </div>
                <div className="text-2xl font-bold text-indigo-800 dark:text-indigo-300">
                  {comparisonResult.comparison_matrix?.length || 0}
                </div>
                <p className="text-[11px] text-indigo-600/80 dark:text-indigo-400/70 mt-0.5">
                  Structured comparison points
                </p>
              </div>
            </div>

            {/* Executive Summary */}
            <div className="p-5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-500" />
                Executive Summary of Differences
              </h4>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                {comparisonResult.executive_summary}
              </p>
            </div>
          </div>

          {/* Module Navigation Tabs */}
          <div className="flex border-b border-slate-200 dark:border-slate-800 gap-2 overflow-x-auto pb-1">
            <button
              onClick={() => setActiveTab('matrix')}
              className={`px-4 py-2.5 text-xs font-bold rounded-lg transition whitespace-nowrap flex items-center gap-2 ${activeTab === 'matrix'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
            >
              <GitCompare className="w-3.5 h-3.5" />
              Side-by-Side Comparison Matrix
            </button>

            <button
              onClick={() => setActiveTab('rules')}
              className={`px-4 py-2.5 text-xs font-bold rounded-lg transition whitespace-nowrap flex items-center gap-2 ${activeTab === 'rules'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
            >
              <Scale className="w-3.5 h-3.5" />
              Rules & Liability Shifts ({comparisonResult.conflicts_or_changes?.length || 0})
            </button>

            <button
              onClick={() => setActiveTab('diff')}
              className={`px-4 py-2.5 text-xs font-bold rounded-lg transition whitespace-nowrap flex items-center gap-2 ${activeTab === 'diff'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Added vs Removed Clauses
            </button>

            <button
              onClick={() => setActiveTab('risk')}
              className={`px-4 py-2.5 text-xs font-bold rounded-lg transition whitespace-nowrap flex items-center gap-2 ${activeTab === 'risk'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
            >
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
              Risk & Compliance Scorecard
            </button>
          </div>

          {/* TAB 1: Comparison Matrix Table */}
          {activeTab === 'matrix' && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden animate-in fade-in duration-150">
              <div className="p-4 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800">
                <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  Structured Comparative Matrix
                </h4>
                <p className="text-xs text-slate-500">
                  Granular side-by-side breakdown across core organizational and legal dimensions
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-100/70 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-700">
                      <th className="p-4 w-1/5">Dimension</th>
                      <th className="p-4 w-1/4">Baseline: {comparisonResult.doc_a_name}</th>
                      <th className="p-4 w-1/4">Revision: {comparisonResult.doc_b_name}</th>
                      <th className="p-4 w-3/10">Key Difference & Impact</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {comparisonResult.comparison_matrix.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                        <td className="p-4 font-bold text-slate-900 dark:text-slate-100 align-top">
                          {row.dimension}
                        </td>
                        <td className="p-4 text-slate-600 dark:text-slate-300 align-top leading-relaxed bg-slate-50/50 dark:bg-slate-900/50">
                          {row.doc_a}
                        </td>
                        <td className="p-4 text-slate-600 dark:text-slate-300 align-top leading-relaxed bg-indigo-50/20 dark:bg-indigo-950/20">
                          {row.doc_b}
                        </td>
                        <td className="p-4 text-indigo-700 dark:text-indigo-300 font-medium align-top leading-relaxed bg-indigo-50/40 dark:bg-indigo-950/30">
                          {row.difference}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: Rules & Liability Shifts */}
          {activeTab === 'rules' && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden animate-in fade-in duration-150">
              <div className="p-4 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800">
                <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                  <Scale className="w-4 h-4 text-amber-500" />
                  Rules & Liabilities Change Matrix
                </h4>
                <p className="text-xs text-slate-500">
                  Highlights modifications in contractual obligations, warranties, deadlines, and liability exposure
                </p>
              </div>

              {comparisonResult.conflicts_or_changes && comparisonResult.conflicts_or_changes.length > 0 ? (
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                  {comparisonResult.conflicts_or_changes.map((item, idx) => (
                    <div key={idx} className="p-5 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <span className="font-bold text-sm text-slate-800 dark:text-slate-100 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-amber-500" />
                          {item.clause}
                        </span>
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${getImpactBadgeClass(item.impact)}`}>
                          {item.impact}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="p-3 rounded-xl bg-slate-100/70 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                          <span className="font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">
                            Baseline Rule (Doc A)
                          </span>
                          <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
                            {item.doc_a_version}
                          </p>
                        </div>

                        <div className="p-3 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200/60 dark:border-indigo-900/40">
                          <span className="font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider block mb-1">
                            Revised Rule (Doc B)
                          </span>
                          <p className="text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                            {item.doc_b_version}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-slate-500">
                  No explicit conflicting rule changes detected between the two versions.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Added vs Removed Clauses */}
          {activeTab === 'diff' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-150">
              {/* Added Clauses */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl border border-emerald-200 dark:border-emerald-900/60 shadow-sm overflow-hidden">
                <div className="p-4 bg-emerald-50/70 dark:bg-emerald-950/40 border-b border-emerald-200/60 dark:border-emerald-900/40 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <h4 className="text-xs font-bold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider">
                      Added in {comparisonResult.doc_b_name}
                    </h4>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200">
                    +{comparisonResult.added_clauses?.length || 0}
                  </span>
                </div>

                <div className="p-5">
                  {comparisonResult.added_clauses && comparisonResult.added_clauses.length > 0 ? (
                    <ul className="space-y-3 text-xs text-slate-700 dark:text-slate-300">
                      {comparisonResult.added_clauses.map((clause, idx) => (
                        <li key={idx} className="flex items-start gap-2.5 p-3 rounded-xl bg-emerald-50/40 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/30">
                          <span className="text-emerald-500 font-bold mt-0.5">•</span>
                          <span className="leading-relaxed font-medium">{clause}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No significant new clauses were introduced.</p>
                  )}
                </div>
              </div>

              {/* Removed Clauses */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl border border-rose-200 dark:border-rose-900/60 shadow-sm overflow-hidden">
                <div className="p-4 bg-rose-50/70 dark:bg-rose-950/40 border-b border-rose-200/60 dark:border-rose-900/40 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MinusCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                    <h4 className="text-xs font-bold text-rose-800 dark:text-rose-300 uppercase tracking-wider">
                      Removed from {comparisonResult.doc_a_name}
                    </h4>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 dark:bg-rose-900 text-rose-800 dark:text-rose-200">
                    -{comparisonResult.removed_clauses?.length || 0}
                  </span>
                </div>

                <div className="p-5">
                  {comparisonResult.removed_clauses && comparisonResult.removed_clauses.length > 0 ? (
                    <ul className="space-y-3 text-xs text-slate-700 dark:text-slate-300">
                      {comparisonResult.removed_clauses.map((clause, idx) => (
                        <li key={idx} className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50/40 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/30">
                          <span className="text-rose-500 font-bold mt-0.5">•</span>
                          <span className="leading-relaxed font-medium">{clause}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No clauses or rules were eliminated.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Risk & Compliance Assessment */}
          {activeTab === 'risk' && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-amber-200 dark:border-amber-900/60 shadow-sm overflow-hidden p-6 space-y-4 animate-in fade-in duration-150">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                    Risk, Liability & Compliance Assessment
                  </h4>
                  <p className="text-xs text-slate-500">
                    Comprehensive audit evaluation of operational and legal exposure
                  </p>
                </div>
              </div>

              <div className="p-5 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 text-xs md:text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-line">
                {comparisonResult.risk_assessment}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Embedded Document Viewer Modal */}
      {viewerDoc && (
        <DocumentViewerModal
          isOpen={true}
          onClose={() => setViewerDoc(null)}
          documentId={viewerDoc.id}
          filename={viewerDoc.name}
        />
      )}
    </div>
  );
};
