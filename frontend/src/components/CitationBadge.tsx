import React, { useState } from 'react';
import { Citation } from '../types';
import { BookOpen, ExternalLink, X, FileText } from 'lucide-react';
import { DocumentViewerModal } from './DocumentViewerModal';

interface CitationBadgeProps {
  citation: Citation;
  index: number;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation, index }) => {
  const [showModal, setShowModal] = useState(false);
  const [showDocViewer, setShowDocViewer] = useState(false);

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/80 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-xs font-medium hover:bg-indigo-100 dark:hover:bg-indigo-900/80 transition-all cursor-pointer shadow-xs"
        title="View source snippet & open document preview"
      >
        <BookOpen className="w-3 h-3" />
        <span>
          [{citation.source_filename}, p.{citation.page_number}]
        </span>
      </button>

      {/* Snippet Preview Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
            <div className="flex items-start justify-between mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                    Source Citation #{index + 1}
                  </h4>
                  <p className="text-xs text-slate-500">
                    {citation.source_filename} • Page {citation.page_number}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                aria-label="Close modal"
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
                {citation.snippet}
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                <span>
                  Chunk ID: <span className="font-mono text-slate-700 dark:text-slate-300">{citation.chunk_id}</span>
                </span>
                {citation.relevance_score !== undefined && (
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">
                    Score: {citation.relevance_score.toFixed(3)}
                  </span>
                )}
              </div>
            </div>

            <div className="mt-5 flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => {
                  setShowModal(false);
                  setShowDocViewer(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>View Full Document (Page {citation.page_number})</span>
              </button>

              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-medium transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Viewer Modal */}
      <DocumentViewerModal
        isOpen={showDocViewer}
        onClose={() => setShowDocViewer(false)}
        documentId={citation.document_id}
        filename={citation.source_filename}
        pageNumber={citation.page_number}
      />
    </>
  );
};
