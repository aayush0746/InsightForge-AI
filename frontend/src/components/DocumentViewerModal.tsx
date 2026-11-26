import React, { useEffect, useState } from 'react';
import { X, ExternalLink, FileText, Download, Loader2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { DocumentPreview } from '../types';

interface DocumentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId?: string;
  filename: string;
  pageNumber?: number;
}

const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.webp']);

export const DocumentViewerModal: React.FC<DocumentViewerModalProps> = ({
  isOpen,
  onClose,
  documentId,
  filename,
  pageNumber = 1,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [activePage, setActivePage] = useState<number>(pageNumber);

  const dotIdx = filename.lastIndexOf('.');
  const ext = dotIdx >= 0 ? filename.slice(dotIdx).toLowerCase() : '';
  const isPdf = ext === '.pdf';
  const isImage = IMAGE_EXTS.has(ext);

  useEffect(() => {
    setActivePage(pageNumber);
  }, [pageNumber]);

  useEffect(() => {
    if (!isOpen || !documentId) return;

    let cancelled = false;
    let createdUrl: string | null = null;

    async function loadContent() {
      setLoading(true);
      setError(null);
      setPreview(null);
      setBlobUrl(null);

      try {
        if (isPdf || isImage) {
          const { blob } = await api.fetchDocumentBlob(documentId!);
          if (cancelled) return;
          createdUrl = URL.createObjectURL(blob);
          setBlobUrl(createdUrl);
        }

        if (!isPdf) {
          const prev = await api.getDocumentPreview(documentId!);
          if (!cancelled) setPreview(prev);
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Failed to load document preview.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadContent();

    return () => {
      cancelled = true;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [isOpen, documentId, isPdf, isImage]);

  if (!isOpen) return null;

  const handleAuthenticatedDownload = async () => {
    if (!documentId) return;
    try {
      const { blob } = await api.fetchDocumentBlob(documentId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      if (preview) {
        const content = preview.pages.map((p) => `--- Section ${p.page} ---\n${p.text}`).join('\n\n');
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}.txt`;
        a.click();
        URL.revokeObjectURL(url);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="flex flex-col w-full max-w-5xl h-[88vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2 truncate">
                <span className="truncate">{filename}</span>
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 shrink-0">
                  {isImage ? 'Image' : `Section ${activePage}`}
                </span>
              </h3>
              <p className="text-xs text-slate-500">Live source verification document preview</p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {blobUrl && (
              <a
                href={blobUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
                title="Open full document in new tab"
              >
                <ExternalLink className="w-4 h-4" />
                <span>Open Tab</span>
              </a>
            )}
            {documentId && (
              <button
                type="button"
                onClick={handleAuthenticatedDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition cursor-pointer"
                title="Download document"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close document preview"
              className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 bg-slate-100 dark:bg-slate-950 relative overflow-hidden flex flex-col">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-2 text-xs">
              <Loader2 className="w-7 h-7 animate-spin text-indigo-500" />
              <span>Loading document content...</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-rose-500 gap-2 text-xs p-6 text-center">
              <AlertCircle className="w-8 h-8" />
              <p className="font-medium">{error}</p>
            </div>
          ) : isPdf && blobUrl ? (
            <iframe
              src={`${blobUrl}#page=${activePage}`}
              title={`Viewer for ${filename}`}
              className="w-full h-full border-none"
            />
          ) : isImage && blobUrl ? (
            <div className="flex-1 overflow-auto p-6 flex flex-col items-center gap-4">
              <img
                src={blobUrl}
                alt={filename}
                className="max-w-full max-h-[60vh] rounded-xl border border-slate-200 dark:border-slate-800 shadow-md object-contain bg-white"
              />
              {preview && preview.pages.length > 0 && (
                <div className="w-full max-w-3xl p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap font-mono">
                  {preview.pages.map((p) => p.text).join('\n\n')}
                </div>
              )}
            </div>
          ) : preview && preview.pages.length > 0 ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              {preview.pages.length > 1 && (
                <div className="px-6 py-2.5 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2 overflow-x-auto">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase shrink-0">
                    Sections ({preview.pages.length}):
                  </span>
                  {preview.pages.map((p) => (
                    <button
                      key={p.page}
                      type="button"
                      onClick={() => setActivePage(p.page)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-mono font-semibold transition shrink-0 cursor-pointer ${
                        activePage === p.page
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/50'
                      }`}
                    >
                      #{p.page}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {preview.pages.map((p) => (
                  <div
                    key={p.page}
                    className={`p-5 rounded-2xl bg-white dark:bg-slate-900 border transition ${
                      p.page === activePage
                        ? 'border-indigo-400 dark:border-indigo-600 ring-2 ring-indigo-500/15'
                        : 'border-slate-200 dark:border-slate-800'
                    }`}
                  >
                    <div className="text-[11px] font-mono font-bold text-indigo-600 dark:text-indigo-400 mb-2">
                      Section / Page {p.page}
                    </div>
                    <pre className="text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap font-sans leading-relaxed">
                      {p.text}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
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
