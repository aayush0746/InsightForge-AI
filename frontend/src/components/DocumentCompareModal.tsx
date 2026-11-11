import React, { useState } from 'react';
import { X, GitCompare, ArrowRight, AlertTriangle, CheckCircle2, MinusCircle, FileText, Loader2 } from 'lucide-react';
import { DocumentMetadata, DocumentComparisonResult } from '../types';
import { api } from '../services/api';

interface DocumentCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  documents: DocumentMetadata[];
}

export const DocumentCompareModal: React.FC<DocumentCompareModalProps> = ({
  isOpen,
  onClose,
  documents,
}) => {
  const [doc1, setDoc1] = useState<string>(documents[0]?.document_id || '');
  const [doc2, setDoc2] = useState<string>(documents[1]?.document_id || documents[0]?.document_id || '');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DocumentComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCompare = async () => {
    if (!doc1 || !doc2) {
      setError('Please select both documents to compare.');
      return;
    }
    if (doc1 === doc2) {
      setError('Please select two different documents to compare.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await api.compareDocuments(doc1, doc2);
      setResult(res.data);
    } catch (err: any) {
      setError(err.message || 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="flex flex-col w-full max-w-5xl max-h-[90vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-slate-100">
                Document Diff & Comparison Matrix
              </h3>
              <p className="text-xs text-slate-500">
                Side-by-side comparative analysis, delta extraction, and risk assessment
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Document Selectors */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700">
            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase">
                Document A (Baseline)
              </label>
              <select
                value={doc1}
                onChange={(e) => setDoc1(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {documents.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.filename} ({d.total_pages} pages)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase">
                Document B (Comparison Target)
              </label>
              <select
                value={doc2}
                onChange={(e) => setDoc2(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {documents.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.filename} ({d.total_pages} pages)
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-center">
            <button
              onClick={handleCompare}
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium shadow-md shadow-indigo-500/20 disabled:opacity-50 transition"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Comparing Documents with Multi-Agent Intelligence...</span>
                </>
              ) : (
                <>
                  <GitCompare className="w-4 h-4" />
                  <span>Run Comparison Matrix</span>
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 rounded-lg border border-red-200 dark:border-red-900">
              {error}
            </div>
          )}

          {/* Results View */}
          {result && (
            <div className="space-y-6 pt-2 border-t border-slate-200 dark:border-slate-800">
              {/* Executive Summary */}
              <div className="p-4 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-900">
                <h4 className="text-sm font-semibold text-indigo-900 dark:text-indigo-300 mb-1">
                  Executive Summary of Differences
                </h4>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {result.executive_summary}
                </p>
              </div>

              {/* Comparison Matrix Table */}
              {result.comparison_matrix && result.comparison_matrix.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">
                    Comparative Matrix
                  </h4>
                  <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-700">
                          <th className="p-3">Dimension</th>
                          <th className="p-3">{result.doc_a_name}</th>
                          <th className="p-3">{result.doc_b_name}</th>
                          <th className="p-3">Key Difference</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                        {result.comparison_matrix.map((row, idx) => (
                          <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                            <td className="p-3 font-medium text-slate-900 dark:text-slate-100">
                              {row.dimension}
                            </td>
                            <td className="p-3 text-slate-600 dark:text-slate-300">{row.doc_a}</td>
                            <td className="p-3 text-slate-600 dark:text-slate-300">{row.doc_b}</td>
                            <td className="p-3 text-indigo-600 dark:text-indigo-400 font-medium">
                              {row.difference}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Added and Removed Clauses */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900 bg-emerald-50/40 dark:bg-emerald-950/20">
                  <h4 className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 uppercase flex items-center gap-1.5 mb-2">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Added in {result.doc_b_name}</span>
                  </h4>
                  <ul className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                    {result.added_clauses && result.added_clauses.length > 0 ? (
                      result.added_clauses.map((clause, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-emerald-500 font-bold">•</span>
                          <span>{clause}</span>
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-400 italic">No significant new clauses added.</li>
                    )}
                  </ul>
                </div>

                <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50/40 dark:bg-rose-950/20">
                  <h4 className="text-xs font-semibold text-rose-800 dark:text-rose-400 uppercase flex items-center gap-1.5 mb-2">
                    <MinusCircle className="w-4 h-4" />
                    <span>Removed from {result.doc_a_name}</span>
                  </h4>
                  <ul className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                    {result.removed_clauses && result.removed_clauses.length > 0 ? (
                      result.removed_clauses.map((clause, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-rose-500 font-bold">•</span>
                          <span>{clause}</span>
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-400 italic">No clauses removed.</li>
                    )}
                  </ul>
                </div>
              </div>

              {/* Risk Assessment */}
              {result.risk_assessment && (
                <div className="p-4 rounded-xl bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900">
                  <div className="flex items-center gap-2 text-amber-800 dark:text-amber-400 font-semibold text-sm mb-1">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Risk & Compliance Assessment</span>
                  </div>
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                    {result.risk_assessment}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

