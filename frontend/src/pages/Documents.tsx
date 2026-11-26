import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  Search,
  GitCompare,
  Eye,
  Globe,
  Link as LinkIcon,
  Loader2,
} from 'lucide-react';
import { api } from '../services/api';
import { DocumentMetadata } from '../types';
import { useAuth } from '../context/AuthContext';
import { DocumentCompareModal } from '../components/DocumentCompareModal';
import { DocumentViewerModal } from '../components/DocumentViewerModal';

const ALLOWED_EXTENSIONS = [
  '.pdf', '.docx', '.pptx', '.xlsx', '.csv', '.tsv',
  '.txt', '.md', '.json', '.html', '.htm', '.xml', '.rtf',
  '.yaml', '.yml', '.png', '.jpg', '.jpeg', '.webp'
];
const ACCEPT_ATTR = ALLOWED_EXTENSIONS.join(',');

export const Documents: React.FC = () => {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadStatusText, setUploadStatusText] = useState('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [urlInput, setUrlInput] = useState('');
  const [ingestingUrl, setIngestingUrl] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [viewerDoc, setViewerDoc] = useState<{ id: string; name: string; page: number } | null>(null);

  const fetchDocuments = async () => {
    try {
      const res = await api.listDocuments();
      setDocuments(res.documents);
    } catch (err: any) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [user]);

  useEffect(() => {
    const handleAuthChange = () => {
      fetchDocuments();
    };
    window.addEventListener('insightforge-auth-change', handleAuthChange);
    return () => window.removeEventListener('insightforge-auth-change', handleAuthChange);
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const fileList = Array.from(files);
    const successes: string[] = [];
    const errors: string[] = [];

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      setUploadStatusText(`Processing ${i + 1}/${fileList.length}: ${file.name}...`);
      const dotIdx = file.name.lastIndexOf('.');
      const ext = dotIdx >= 0 ? file.name.slice(dotIdx).toLowerCase() : '';
      if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
        errors.push(`${file.name}: unsupported format '${ext || '(none)'}'`);
        continue;
      }

      try {
        await api.uploadDocument(file);
        successes.push(file.name);
      } catch (err: any) {
        errors.push(`${file.name}: ${err.message || 'Upload failed'}`);
      }
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setUploadStatusText('');
    setUploading(false);

    if (successes.length > 0) {
      setUploadSuccess(
        successes.length === 1
          ? `Document '${successes[0]}' processed and indexed successfully.`
          : `Processed and indexed ${successes.length} documents: ${successes.join(', ')}.`
      );
      await fetchDocuments();
      window.dispatchEvent(new CustomEvent('insightforge-docs-change'));
    }
    if (errors.length > 0) {
      setUploadError(errors.join(' | '));
    }
  };

  const handleUrlIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim() || ingestingUrl) return;

    setIngestingUrl(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await api.ingestUrl(urlInput.trim());
      setUploadSuccess(res.message);
      setUrlInput('');
      await fetchDocuments();
      window.dispatchEvent(new CustomEvent('insightforge-docs-change'));
    } catch (err: any) {
      setUploadError(err.message || 'Failed to ingest URL.');
    } finally {
      setIngestingUrl(false);
    }
  };

  const handleDelete = async (docId: string) => {
    setDeletingId(docId);
    setUploadError(null);
    try {
      setDocuments((prev) => prev.filter((d) => d.document_id !== docId));
      await api.deleteDocument(docId);
      setUploadSuccess('Document and vector embeddings deleted successfully.');
      window.dispatchEvent(new CustomEvent('insightforge-docs-change'));
      setTimeout(() => setUploadSuccess(null), 3000);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to delete document.');
      await fetchDocuments();
    } finally {
      setDeletingId(null);
    }
  };

  const filteredDocs = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-in fade-in duration-200">
      {/* Upload & Ingest Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 p-8 rounded-3xl bg-white dark:bg-slate-900 border-2 border-dashed border-slate-200 dark:border-slate-800 text-center relative hover:border-indigo-500/50 transition">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ACCEPT_ATTR}
            onChange={handleFileSelect}
            disabled={uploading}
            aria-label="Upload research files"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          />
          <div className="max-w-lg mx-auto space-y-3 pointer-events-none">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 flex items-center justify-center mx-auto">
              <Upload className={`w-6 h-6 ${uploading ? 'animate-bounce' : ''}`} />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                {uploading ? (uploadStatusText || 'Processing & Indexing Document...') : 'Upload Research Files (Single or Batch)'}
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Drag &amp; drop or click to browse multiple files. Max size: 25 MB each.
              </p>
            </div>
            <span className="inline-block px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-[11px] font-mono text-slate-500">
              PDF, DOCX, PPTX, XLSX, CSV, TSV, TXT, MD, JSON, HTML, XML, RTF, YAML, PNG, JPG, WEBP
            </span>
          </div>
        </div>

        {/* Live URL Scraper Ingestion Card */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
              <Globe className="w-5 h-5" />
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Ingest Live Webpage
              </h3>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Paste any public article or website URL. InsightForge will scrape, chunk, and index it into ChromaDB.
            </p>
          </div>

          <form onSubmit={handleUrlIngest} className="space-y-3">
            <div className="relative">
              <LinkIcon className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
              <input
                type="url"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/article"
                aria-label="Website URL to ingest"
                required
                className="w-full pl-8 pr-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <button
              type="submit"
              disabled={ingestingUrl || !urlInput.trim()}
              className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center justify-center space-x-2 transition cursor-pointer shadow-sm"
            >
              {ingestingUrl ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Scraping URL...</span>
                </>
              ) : (
                <span>Ingest Webpage</span>
              )}
            </button>
          </form>
        </div>
      </div>

      {uploadError && (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center space-x-2" role="alert">
          <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}
      {uploadSuccess && (
        <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs flex items-center space-x-2" role="status">
          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {/* Documents Table */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
              Indexed Documents ({documents.length})
            </h3>
            <p className="text-xs text-slate-500">
              ChromaDB persistent vector store collection &amp; semantic index
            </p>
          </div>

          <div className="flex items-center gap-3">
            {documents.length >= 2 && (
              <button
                type="button"
                onClick={() => setCompareModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 border border-indigo-200 dark:border-indigo-800 text-xs font-semibold transition cursor-pointer"
              >
                <GitCompare className="w-4 h-4" />
                <span>Compare 2 Docs</span>
              </button>
            )}

            <search className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="search"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter by filename..."
                aria-label="Filter documents by filename"
                className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
              />
            </search>
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400">Loading documents...</div>
        ) : filteredDocs.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-40 text-slate-400" />
            <p>No documents found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-medium">
                  <th className="pb-3 font-semibold">Document Name</th>
                  <th className="pb-3 font-semibold">Size</th>
                  <th className="pb-3 font-semibold">Pages / Sections</th>
                  <th className="pb-3 font-semibold">Chunks</th>
                  <th className="pb-3 font-semibold">Uploaded</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {filteredDocs.map((doc) => (
                  <tr
                    key={doc.document_id}
                    className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition"
                  >
                    <td className="py-3 font-medium text-slate-800 dark:text-slate-200 flex items-center space-x-2">
                      <FileCheck className="w-4 h-4 text-indigo-500 shrink-0" />
                      <span className="truncate max-w-xs">{doc.filename}</span>
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      {formatBytes(doc.file_size_bytes)}
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      {doc.total_pages} {doc.total_pages === 1 ? 'section' : 'sections'}
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      <span className="px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-semibold">
                        {doc.total_chunks}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      {new Date(doc.upload_timestamp).toLocaleDateString()}
                    </td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
                        {doc.status}
                      </span>
                    </td>
                    <td className="py-3 text-right space-x-1">
                      <button
                        type="button"
                        onClick={() =>
                          setViewerDoc({ id: doc.document_id, name: doc.filename, page: 1 })
                        }
                        className="p-1.5 text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
                        title="Preview document"
                        aria-label={`Preview ${doc.filename}`}
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(doc.document_id)}
                        disabled={deletingId === doc.document_id}
                        className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/30 transition cursor-pointer disabled:opacity-50"
                        title="Delete document"
                        aria-label={`Delete ${doc.filename}`}
                      >
                        {deletingId === doc.document_id ? (
                          <Loader2 className="w-4 h-4 animate-spin text-rose-500" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <DocumentCompareModal
        isOpen={compareModalOpen}
        onClose={() => setCompareModalOpen(false)}
        documents={documents}
      />

      {viewerDoc && (
        <DocumentViewerModal
          isOpen={true}
          onClose={() => setViewerDoc(null)}
          documentId={viewerDoc.id}
          filename={viewerDoc.name}
          pageNumber={viewerDoc.page}
        />
      )}
    </div>
  );
};
