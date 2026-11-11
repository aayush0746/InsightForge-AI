import React from 'react';
import { X, ExternalLink, FileText, Download } from 'lucide-react';
import { api } from '../services/api';

interface DocumentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId?: string;
  filename: string;
  pageNumber?: number;
}

export const DocumentViewerModal: React.FC<DocumentViewerModalProps> = ({
  isOpen,
  onClose,
  documentId,
  filename,
  pageNumber = 1,
}) => {
  if (!isOpen) return null;

  const fileUrl = documentId ? api.getDocumentFileUrl(documentId) : '';
  const viewerUrl = fileUrl ? `${fileUrl}#page=${pageNumber}` : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="flex flex-col w-full max-w-5xl h-[88vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <span>{filename}</span>
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
                  Page {pageNumber}
                </span>
              </h3>
              <p className="text-xs text-slate-500">Live source verification document preview</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {fileUrl && (
              <>
                <a
                  href={fileUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
                  title="Open full document in new tab"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>Open Tab</span>
                </a>
                <a
                  href={fileUrl}
                  download={filename}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
                  title="Download document"
                >
                  <Download className="w-4 h-4" />
                  <span>Download</span>
                </a>
              </>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* PDF / Document Embed Viewer */}
        <div className="flex-1 bg-slate-100 dark:bg-slate-950 relative">
          {viewerUrl ? (
            <iframe
              src={viewerUrl}
              title={`Viewer for ${filename}`}
              className="w-full h-full border-none"
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
              <FileText className="w-12 h-12 mb-2 opacity-50" />
              <p>Document source preview is unavailable.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

