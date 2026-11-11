import React, { useState, useEffect } from 'react';
import {
  Send,
  BrainCircuit,
  Zap,
  CheckCircle2,
  AlertCircle,
  FileText,
  ShieldCheck,
  ChevronRight,
  Filter,
  Download,
  Printer,
  Sparkles,
  Globe,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  ChatResponse,
  ResearchReport,
  DocumentMetadata,
  ChatMessage,
} from '../types';
import { CitationBadge } from '../components/CitationBadge';
import { AgentTimeline } from '../components/AgentTimeline';
import { AudioBriefing } from '../components/AudioBriefing';
import { VoiceInputButton } from '../components/VoiceInputButton';
import { InteractiveChart } from '../components/InteractiveChart';

const SAMPLE_QUESTIONS = [
  "What is the required attendance percentage for students to appear in exams?",
  "How can students apply for leave and who is the approving authority?",
  "What is the compensation and stipend structure during training and probation?",
  "Explain the comprehensive student guidelines, leave policies, and code of conduct."
];

export const Workspace: React.FC = () => {
  const { user, isAuthenticated, openAuthModal } = useAuth();

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'fast' | 'agentic'>('fast');
  const [enableWebSearch, setEnableWebSearch] = useState<boolean>(false);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string>('Planner Agent');
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Conversation history for multi-turn chat
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(() => {
    try {
      if (user?.id) {
        const saved = localStorage.getItem(`insightforge_workspace_chat_${user.id}`);
        return saved ? JSON.parse(saved) : [];
      } else {
        const saved = sessionStorage.getItem('insightforge_guest_chat');
        return saved ? JSON.parse(saved) : [];
      }
    } catch {
      return [];
    }
  });

  // Results
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null);
  const [researchReport, setResearchReport] = useState<ResearchReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sync chat history to storage (localStorage for users, sessionStorage for guests)
  useEffect(() => {
    try {
      if (user?.id) {
        localStorage.setItem(`insightforge_workspace_chat_${user.id}`, JSON.stringify(chatHistory));
      } else {
        sessionStorage.setItem('insightforge_guest_chat', JSON.stringify(chatHistory));
      }
    } catch (e) {
      // ignore
    }
  }, [chatHistory, user]);

  const loadDocuments = async () => {
    try {
      const res = await api.listDocuments();
      setDocuments(res.documents);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const loadChat = async () => {
    if (user?.id) {
      // 1. Fetch persistent chat history from Supabase Cloud PostgreSQL
      try {
        const res = await api.getChatHistory();
        if (res?.history && res.history.length > 0) {
          const formatted = res.history.map((h) => ({ role: h.role, content: h.content }));
          setChatHistory(formatted);
          localStorage.setItem(`insightforge_workspace_chat_${user.id}`, JSON.stringify(formatted));
          return;
        }
      } catch (e) {
        console.warn('Failed to fetch cloud chat history:', e);
      }
      // Fallback to local cache if offline or newly created
      try {
        const saved = localStorage.getItem(`insightforge_workspace_chat_${user.id}`);
        setChatHistory(saved ? JSON.parse(saved) : []);
      } catch {
        setChatHistory([]);
      }
    } else {
      // Guest mode: strictly ephemeral sessionStorage (never saved to cloud)
      try {
        const saved = sessionStorage.getItem('insightforge_guest_chat');
        setChatHistory(saved ? JSON.parse(saved) : []);
      } catch {
        setChatHistory([]);
      }
    }
  };

  useEffect(() => {
    loadDocuments();
    loadChat();
  }, [user]);

  useEffect(() => {
    const handleAuthChange = () => {
      setChatResult(null);
      setResearchReport(null);
      setQuery('');
      loadDocuments();
      loadChat();
    };
    window.addEventListener('insightforge-auth-change', handleAuthChange);
    return () => window.removeEventListener('insightforge-auth-change', handleAuthChange);
  }, []);

  const handleClearChat = async () => {
    setChatHistory([]);
    setChatResult(null);
    setResearchReport(null);
    if (user?.id) {
      localStorage.removeItem(`insightforge_workspace_chat_${user.id}`);
      try {
        await api.clearChatHistory();
      } catch (e) {
        console.error('Failed to clear cloud chat history:', e);
      }
    } else {
      sessionStorage.removeItem('insightforge_guest_chat');
      try {
        await api.clearGuestData();
      } catch {
        // ignore
      }
    }
  };

  const exportToMarkdown = (title: string, content: string) => {
    const blob = new Blob([`# ${title}\n\nGenerated by InsightForge AI\n\n---\n\n${content}`], {
      type: 'text/markdown',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/[^a-z0-9]/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;

    const currentQuery = query.trim();
    setErrorMsg(null);
    setIsLoading(true);
    setChatResult(null);
    setResearchReport(null);
    setElapsedSeconds(0);

    const startTime = Date.now();
    const timerInterval = setInterval(() => {
      setElapsedSeconds(Number(((Date.now() - startTime) / 1000).toFixed(1)));
    }, 100);

    const docFilter = selectedDocId === 'all' ? undefined : [selectedDocId];

    if (mode === 'fast') {
      try {
        const res = await api.askChat({
          question: currentQuery,
          document_ids: docFilter,
          use_reranker: true,
          enable_web_search: enableWebSearch,
          top_k: 8,
          top_n: 4,
          history: chatHistory.map((h) => ({ role: h.role, content: h.content })),
        });
        setChatResult(res);
        // Append to conversational memory
        setChatHistory((prev) => [
          ...prev,
          { role: 'user', content: currentQuery },
          { role: 'assistant', content: res.answer },
        ]);
      } catch (err: any) {
        const msg = err.message || '';
        if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
          setErrorMsg('Cannot connect to backend server. Please verify backend is running on http://127.0.0.1:8000.');
        } else {
          setErrorMsg(msg || 'Failed to generate grounded RAG response.');
        }
      } finally {
        clearInterval(timerInterval);
        setIsLoading(false);
      }
    } else {
      // Multi-Agent Workflow
      setActiveAgent('Planner Agent');
      const agentInterval = setInterval(() => {
        setActiveAgent((prev) => {
          if (prev === 'Planner Agent') return 'Research Agent';
          if (prev === 'Research Agent') return 'Analyst Agent';
          if (prev === 'Analyst Agent') return 'Critic & Fact-Checker';
          return 'Synthesizer Agent';
        });
      }, 2500);

      try {
        const res = await api.startResearch({
          question: currentQuery,
          document_ids: docFilter,
          deep_analysis: true,
          enable_web_search: enableWebSearch,
          max_subtasks: 2,
        });
        setResearchReport(res.report);
        setChatHistory((prev) => [
          ...prev,
          { role: 'user', content: currentQuery },
          { role: 'assistant', content: res.report.executive_summary },
        ]);
      } catch (err: any) {
        const msg = err.message || '';
        if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
          setErrorMsg('Cannot connect to backend server. Please verify backend is running on http://127.0.0.1:8000.');
        } else {
          setErrorMsg(msg || 'Multi-agent research workflow failed.');
        }
      } finally {
        clearInterval(agentInterval);
        clearInterval(timerInterval);
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-in fade-in duration-200">
      {/* Session Status Banner */}
      {isAuthenticated && user ? (
        <div className="p-4 rounded-2xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200/70 dark:border-indigo-900/50 flex flex-wrap items-center justify-between gap-3 text-xs text-indigo-900 dark:text-indigo-200">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
            <span>
              <strong>Private Account Active:</strong> Logged in as <strong>{user.email}</strong>. Your research, documents, and history are strictly isolated.
            </span>
          </div>
          {chatHistory.length > 0 && (
            <button
              type="button"
              onClick={handleClearChat}
              className="px-2.5 py-1 rounded-lg bg-indigo-100 hover:bg-indigo-200 dark:bg-indigo-900/60 dark:hover:bg-indigo-800 text-indigo-800 dark:text-indigo-200 font-semibold text-[11px] transition cursor-pointer"
            >
              Clear Chat History ({chatHistory.length})
            </button>
          )}
        </div>
      ) : (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/25 flex flex-wrap items-center justify-between gap-3 text-xs text-amber-900 dark:text-amber-200">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
            <span>
              <strong>Temporary Guest Session:</strong> You are exploring in guest mode. Messages and questions exist only for this visit and will not be saved permanently.
            </span>
          </div>
          <div className="flex items-center gap-2">
            {chatHistory.length > 0 && (
              <button
                type="button"
                onClick={handleClearChat}
                className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-900 dark:text-amber-100 font-semibold text-[11px] transition cursor-pointer"
              >
                Clear Temporary Chat
              </button>
            )}
            <button
              type="button"
              onClick={() => openAuthModal('signup')}
              className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-[11px] transition shadow-xs cursor-pointer"
            >
              Sign Up to Save Permanently
            </button>
          </div>
        </div>
      )}

      {/* Search & Query Bar Card */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
        {/* Mode Selector & Filter */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-1.5 p-1 rounded-xl bg-slate-100 dark:bg-slate-800">
            <button
              onClick={() => setMode('fast')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${mode === 'fast'
                ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Fast Grounded RAG</span>
            </button>
            <button
              onClick={() => setMode('agentic')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${mode === 'agentic'
                ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
            >
              <BrainCircuit className="w-3.5 h-3.5" />
              <span>Multi-Agent Research (Deep)</span>
            </button>
          </div>

          {/* Live Web Augmentation Toggle & Document Scope */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setEnableWebSearch(!enableWebSearch)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition cursor-pointer ${enableWebSearch
                ? 'bg-blue-50 dark:bg-blue-950/50 border-blue-300 dark:border-blue-800 text-blue-600 dark:text-blue-400 shadow-xs'
                : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              title="Toggle between Docs Only and Hybrid Docs + Live Web Search"
            >
              <Globe className={`w-3.5 h-3.5 ${enableWebSearch ? 'text-blue-500 animate-spin-slow' : ''}`} />
              <span>{enableWebSearch ? 'Hybrid: Docs + Live Web' : 'Internal Docs Only'}</span>
            </button>

            {/* Document Scope Filter */}
            <div className="flex items-center space-x-1.5 text-xs text-slate-500">
              <Filter className="w-3.5 h-3.5" />
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
              >
                <option value="all">All Documents ({documents.length})</option>
                {documents.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.filename} ({d.total_chunks} chunks)
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Input Form with Voice Dictation */}
        <form onSubmit={handleSubmit} className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="Ask a complex research question across your documents..."
            rows={3}
            className="w-full p-4 pr-32 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/80 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 transition resize-none leading-relaxed"
          />

          <div className="absolute right-3 bottom-3 flex items-center space-x-1.5">
            {/* Voice Input Button */}
            <VoiceInputButton
              onTranscript={(txt) => setQuery((prev) => (prev ? `${prev} ${txt}` : txt))}
              disabled={isLoading}
            />

            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 transition shadow-md shadow-indigo-600/20 cursor-pointer"
            >
              {isLoading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Researching...</span>
                </>
              ) : (
                <>
                  <span>Send</span>
                  <Send className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Sample Question Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] text-slate-400 font-medium">Try asking:</span>
          {SAMPLE_QUESTIONS.map((sq, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setQuery(sq)}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/60 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-300 transition text-left"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Loading State Banner */}
      {isLoading && (
        <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm text-center space-y-4 animate-in fade-in">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 flex items-center justify-center mx-auto animate-bounce">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center justify-center space-x-2">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                {mode === 'agentic'
                  ? `Autonomous Agent Active: ${activeAgent}`
                  : 'Fast Grounded RAG Ingesting & Answering'}
              </h3>
              <span className="px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 font-mono text-xs font-bold">
                {elapsedSeconds}s
              </span>
            </div>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              {mode === 'agentic'
                ? 'Planner, Research, Analyst, Critic, Fact-Checker, and Synthesizer collaborating...'
                : 'BM25 + ChromaDB semantic retrieval & neural CrossEncoder reranking...'}
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-500" />
          <p className="font-medium">{errorMsg}</p>
        </div>
      )}

      {/* FAST RAG ANSWER DISPLAY */}
      {chatResult && (
        <div className="p-7 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center space-x-2">
              <span className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600">
                <Zap className="w-4 h-4" />
              </span>
              <div>
                <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                  Grounded RAG Answer
                </h3>
                <p className="text-xs text-slate-400">
                  Completed in{' '}
                  <strong className="text-indigo-600 dark:text-indigo-400 font-mono">
                    {elapsedSeconds}s
                  </strong>{' '}
                  • Retrieved {chatResult.retrieved_chunks_count} chunks • Reranked to top{' '}
                  {chatResult.reranked_chunks_count}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Audio Briefing Player */}
              <AudioBriefing text={chatResult.answer} topic={chatResult.question || query} />

              {/* Export Buttons */}
              <button
                onClick={() => exportToMarkdown('Grounded_RAG_Answer', chatResult.answer)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition"
                title="Download as Markdown"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export MD</span>
              </button>

              <button
                onClick={() => window.print()}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition"
                title="Print or Save as PDF"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print PDF</span>
              </button>

              <span
                className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 ${chatResult.is_grounded
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                  : 'bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
                  }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                {chatResult.is_grounded ? 'Grounded in Documents' : 'Information Unavailable'}
              </span>
            </div>
          </div>

          {/* Answer Body */}
          <div className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap font-normal">
            {chatResult.answer}
          </div>

          {/* Interactive Chart (if quantitative data was returned) */}
          {chatResult.chart_data && <InteractiveChart chartData={chatResult.chart_data} />}

          {/* Citations Row */}
          {chatResult.citations.length > 0 && (
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Sources & Citations ({chatResult.citations.length}) — Click to preview document
              </span>
              <div className="flex flex-wrap gap-2 pt-1">
                {chatResult.citations.map((cit, idx) => (
                  <CitationBadge key={idx} citation={cit} index={idx} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* MULTI-AGENT DEEP RESEARCH REPORT DISPLAY */}
      {researchReport && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Report Body (Left 2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            <div className="p-7 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-6">
              {/* Header */}
              <div className="border-b border-slate-100 dark:border-slate-800 pb-5">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 text-xs font-bold font-mono">
                      {researchReport.research_id}
                    </span>
                    <div className="flex items-center space-x-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-semibold px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>{researchReport.grounding_score}% Grounding Verified</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <AudioBriefing
                      text={researchReport.executive_summary}
                      title="Audio Executive Briefing"
                      topic={researchReport.question}
                    />

                    <button
                      onClick={() =>
                        exportToMarkdown(
                          `Research_Report_${researchReport.research_id}`,
                          `## Question\n${researchReport.question}\n\n## Executive Summary\n${researchReport.executive_summary}\n\n## Methodology\n${researchReport.methodology}\n\n## Key Findings\n${researchReport.key_findings.map((f) => `- ${f}`).join('\n')}\n\n## Evidence Analysis\n${researchReport.evidence_analysis}\n\n## Recommendations\n${researchReport.recommendations.map((r) => `- ${r}`).join('\n')}`
                        )
                      }
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition"
                      title="Download as Markdown"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Export MD</span>
                    </button>

                    <button
                      onClick={() => window.print()}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition"
                      title="Print or Save as PDF"
                    >
                      <Printer className="w-3.5 h-3.5" />
                      <span>Print PDF</span>
                    </button>
                  </div>
                </div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                  {researchReport.question}
                </h2>
              </div>

              {/* 1. Executive Summary */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  1. Executive Summary
                </h4>
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {researchReport.executive_summary}
                </div>
              </div>

              {/* Interactive Chart */}
              {researchReport.chart_data && (
                <InteractiveChart chartData={researchReport.chart_data} />
              )}

              {/* 2. Key Findings */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  2. Key Findings (Document Grounded)
                </h4>
                <ul className="space-y-2">
                  {researchReport.key_findings.map((finding, idx) => (
                    <li
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-50/70 dark:bg-slate-800/30 border border-slate-100 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 flex items-start space-x-3"
                    >
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">{finding}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 3. In-Depth Analysis */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  3. In-Depth Evidence Synthesis
                </h4>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {researchReport.evidence_analysis}
                </p>
              </div>

              {/* 4. AI Interpretations vs Direct Facts */}
              {researchReport.ai_interpretations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    4. Analytical Implications (AI Interpretation)
                  </h4>
                  <ul className="space-y-1.5 list-disc list-inside text-xs text-slate-600 dark:text-slate-400">
                    {researchReport.ai_interpretations.map((item, idx) => (
                      <li key={idx} className="leading-relaxed">
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 5. Recommendations & Action Items */}
              {researchReport.recommendations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                    5. Strategic Recommendations
                  </h4>
                  <div className="grid grid-cols-1 gap-2">
                    {researchReport.recommendations.map((rec, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 text-xs text-emerald-950 dark:text-emerald-200 flex items-start space-x-2.5"
                      >
                        <ChevronRight className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span className="leading-relaxed font-medium">{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 6. Citations */}
              <div className="space-y-2 pt-4 border-t border-slate-100 dark:border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Sources & Grounded Chunks ({researchReport.citations.length})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {researchReport.citations.map((cit, idx) => (
                    <CitationBadge key={idx} citation={cit} index={idx} />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Agent Workflow & Fact Checks */}
          <div className="space-y-6">
            {/* Agent Timeline */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
              <AgentTimeline steps={researchReport.agent_steps} />
            </div>

            {/* Fact Checker Audit Card */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  Fact-Checker Audit
                </h4>
                <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400">
                  {researchReport.grounding_score}%
                </span>
              </div>

              <div className="space-y-2.5">
                {researchReport.fact_check_results.map((fc, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded-xl border text-xs space-y-1 ${fc.is_supported
                      ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-100 dark:border-emerald-900/40'
                      : 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-100 dark:border-rose-900/40'
                      }`}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`font-semibold text-[11px] ${fc.is_supported
                          ? 'text-emerald-700 dark:text-emerald-300'
                          : 'text-rose-700 dark:text-rose-300'
                          }`}
                      >
                        {fc.is_supported ? 'Verified Grounded' : 'Unsupported / Flagged'}
                      </span>
                      <span className="font-mono text-[10px] text-slate-400">
                        {(fc.confidence * 100).toFixed(0)}% Conf.
                      </span>
                    </div>
                    <p className="text-slate-700 dark:text-slate-300 font-medium">{fc.claim}</p>
                    {fc.source_citation && (
                      <p className="text-[10px] text-slate-500 font-mono">
                        Ref: {fc.source_citation}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
