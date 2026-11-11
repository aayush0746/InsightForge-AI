import React, { useState, useEffect, useRef } from 'react';
import {
  FolderKanban,
  Plus,
  MessageSquare,
  FileText,
  Trash2,
  Send,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Globe,
  Layers,
  ChevronRight,
  Loader2,
  AlertCircle,
  Eye,
  CornerDownRight,
  Check,
  Zap
} from 'lucide-react';
import { Project, ProjectThread, ThreadMessage, DocumentMetadata } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { VoiceInputButton } from '../components/VoiceInputButton';
import { AudioBriefing } from '../components/AudioBriefing';
import { InteractiveChart } from '../components/InteractiveChart';
import { DocumentViewerModal } from '../components/DocumentViewerModal';

const QUICK_FOLLOWUPS = [
  'Elaborate on point 2 in more detail',
  'Rewrite that table in alphabetical order',
  'Summarize the core takeaways in 3 bullet points',
  'What are the key liabilities or penalties mentioned?',
  'Compare this with standard market practices'
];

export const Projects: React.FC = () => {
  const { user, isAuthenticated, openAuthModal } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [threads, setThreads] = useState<ProjectThread[]>([]);
  const [activeThread, setActiveThread] = useState<ProjectThread | null>(null);

  const [allDocs, setAllDocs] = useState<DocumentMetadata[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  const [inputQuery, setInputQuery] = useState('');
  const [enableWebSearch, setEnableWebSearch] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // New Project Modal
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjName, setNewProjName] = useState('');
  const [newProjDesc, setNewProjDesc] = useState('');
  const [newProjColor, setNewProjColor] = useState('indigo');

  // Assign Document Modal
  const [showAssignDocModal, setShowAssignDocModal] = useState(false);
  const [selectedDocToAssign, setSelectedDocToAssign] = useState('');

  // Document Viewer Modal
  const [viewerDoc, setViewerDoc] = useState<{ id: string; name: string } | null>(null);

  // Active view tab in project: 'chat' | 'documents'
  const [projectTab, setProjectTab] = useState<'chat' | 'documents'>('chat');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadProjectsAndDocs();
  }, [user]);

  useEffect(() => {
    const handleAuthChange = () => {
      setActiveProject(null);
      setActiveThread(null);
      setThreads([]);
      loadProjectsAndDocs();
    };
    window.addEventListener('insightforge-auth-change', handleAuthChange);
    return () => window.removeEventListener('insightforge-auth-change', handleAuthChange);
  }, []);

  const handleClearGuestSession = async () => {
    try {
      await api.clearGuestData();
      setActiveThread(null);
      await loadProjectsAndDocs();
    } catch (err) {
      console.error('Failed to clear guest session:', err);
    }
  };

  const loadProjectsAndDocs = async () => {
    try {
      setIsLoadingProjects(true);
      const [projList, docsRes] = await Promise.all([
        api.listProjects(),
        api.listDocuments()
      ]);
      setProjects(projList);
      setAllDocs(docsRes.documents);

      if (projList.length > 0) {
        selectProject(projList[0]);
      } else {
        setActiveProject(null);
        setActiveThread(null);
        setThreads([]);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load projects');
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const selectProject = async (proj: Project) => {
    setActiveProject(proj);
    setErrorMessage(null);
    try {
      setIsLoadingThreads(true);
      const threadList = await api.listThreads(proj.id);
      setThreads(threadList);
      if (threadList.length > 0) {
        setActiveThread(threadList[0]);
      } else {
        // Create initial thread
        const newTh = await api.createThread(proj.id, 'General Discussion');
        setThreads([newTh]);
        setActiveThread(newTh);
      }
    } catch (err: any) {
      console.error('Failed to load threads:', err);
    } finally {
      setIsLoadingThreads(false);
    }
  };

  const selectThread = async (thread: ProjectThread) => {
    try {
      if (!activeProject) return;
      const full = await api.getThread(activeProject.id, thread.id);
      setActiveThread(full);
    } catch (err) {
      setActiveThread(thread);
    }
  };

  const handleCreateNewThread = async () => {
    if (!activeProject) return;
    try {
      const th = await api.createThread(activeProject.id, `Inquiry ${threads.length + 1}`);
      setThreads([th, ...threads]);
      setActiveThread(th);
      setProjectTab('chat');
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not create thread');
    }
  };

  const handleSendMessage = async (customQuery?: string) => {
    const textToSend = customQuery || inputQuery;
    if (!textToSend.trim() || !activeProject || !activeThread || isSendingMessage) return;

    try {
      setIsSendingMessage(true);
      setErrorMessage(null);
      setInputQuery('');

      const res = await api.sendThreadMessage(
        activeProject.id,
        activeThread.id,
        textToSend,
        enableWebSearch
      );

      setActiveThread(res.thread);
      // Update thread title in sidebar list
      setThreads((prev) =>
        prev.map((t) => (t.id === res.thread.id ? res.thread : t))
      );
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to send message');
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName.trim()) return;

    try {
      const created = await api.createProject({
        name: newProjName.trim(),
        description: newProjDesc.trim(),
        color: newProjColor
      });
      setProjects([...projects, created]);
      selectProject(created);
      setShowNewProjectModal(false);
      setNewProjName('');
      setNewProjDesc('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to create workspace collection');
    }
  };

  const handleAssignDocument = async () => {
    if (!activeProject || !selectedDocToAssign) return;
    try {
      await api.assignDocToProject(activeProject.id, selectedDocToAssign);
      const updated = await api.getProject(activeProject.id);
      setActiveProject(updated);
      setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setShowAssignDocModal(false);
      setSelectedDocToAssign('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to assign document');
    }
  };

  const handleRemoveDocument = async (docId: string) => {
    if (!activeProject) return;
    try {
      await api.removeDocFromProject(activeProject.id, docId);
      const updated = await api.getProject(activeProject.id);
      setActiveProject(updated);
      setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to remove document');
    }
  };

  const projectDocs = allDocs.filter((d) => activeProject?.document_ids.includes(d.document_id));
  const unassignedDocs = allDocs.filter((d) => !activeProject?.document_ids.includes(d.document_id));

  const getColorClasses = (color: string) => {
    switch (color) {
      case 'emerald':
        return 'from-emerald-500 to-teal-600 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40';
      case 'amber':
        return 'from-amber-500 to-orange-600 border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40';
      case 'rose':
        return 'from-rose-500 to-pink-600 border-rose-500/30 text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40';
      default:
        return 'from-indigo-500 to-violet-600 border-indigo-500/30 text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40';
    }
  };

  return (
    <div className="flex h-[calc(100vh-8.5rem)] gap-5 max-w-[95rem] mx-auto">
      {/* 1. LEFT COLUMN: Workspaces & Threads Navigation */}
      <div className="w-80 flex flex-col bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden shrink-0">
        {/* Workspace Collections Header */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <FolderKanban className="w-4 h-4" />
            </div>
            <span className="font-bold text-xs uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Workspace Collections
            </span>
          </div>
          <button
            onClick={() => setShowNewProjectModal(true)}
            className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 transition"
            title="Create New Isolated Collection"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Project Selector List */}
        <div className="p-3 border-b border-slate-100 dark:border-slate-800 space-y-1.5 max-h-48 overflow-y-auto">
          {projects.map((proj) => {
            const isSelected = activeProject?.id === proj.id;
            return (
              <button
                key={proj.id}
                onClick={() => selectProject(proj)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-xs font-semibold flex items-center justify-between transition ${isSelected
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                  }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className={`w-2 h-2 rounded-full ${isSelected ? 'bg-white' : 'bg-indigo-500'}`} />
                  <span className="truncate">{proj.name}</span>
                </div>
                <div className="flex items-center gap-1.5 text-[10px] opacity-80 shrink-0">
                  <span>{proj.document_count} files</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Threads Header */}
        <div className="p-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/30">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Threads ({threads.length})</span>
          </div>
          <button
            onClick={handleCreateNewThread}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-indigo-600 text-white text-[11px] font-semibold hover:bg-indigo-700 transition"
          >
            <Plus className="w-3 h-3" /> New
          </button>
        </div>

        {/* Threads List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoadingThreads ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading threads...</div>
          ) : threads.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">No threads yet. Click New!</div>
          ) : (
            threads.map((t) => {
              const isSelected = activeThread?.id === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => selectThread(t)}
                  className={`w-full text-left p-2.5 rounded-xl text-xs transition flex flex-col gap-1 ${isSelected
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-900 dark:text-indigo-200 border border-indigo-200 dark:border-indigo-800 font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 border border-transparent'
                    }`}
                >
                  <p className="line-clamp-1 leading-snug">{t.title}</p>
                  <span className="text-[10px] text-slate-400">
                    {t.messages.length} messages • {new Date(t.updated_at).toLocaleDateString()}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* 2. RIGHT COLUMN: Main Project Workspace & Thread Chat */}
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
        {/* Project Header & Scoping Notice */}
        {activeProject && (
          <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4 bg-slate-50/60 dark:bg-slate-800/40">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base text-slate-900 dark:text-slate-100">
                  {activeProject.name}
                </span>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200/50 dark:border-indigo-800">
                  <Lock className="w-3 h-3 text-indigo-500" />
                  Isolated Collection
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {activeProject.description || 'Dedicated workspace collection with isolated ChromaDB vector indexing'}
              </p>
            </div>

            {/* View Switcher: Chat Thread vs Assigned Documents */}
            <div className="flex items-center gap-2">
              <div className="flex p-1 rounded-xl bg-slate-200/60 dark:bg-slate-800 text-xs font-semibold">
                <button
                  onClick={() => setProjectTab('chat')}
                  className={`px-3 py-1.5 rounded-lg transition ${projectTab === 'chat'
                      ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400'
                    }`}
                >
                  Chat Thread
                </button>
                <button
                  onClick={() => setProjectTab('documents')}
                  className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${projectTab === 'documents'
                      ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400'
                    }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Files ({projectDocs.length})</span>
                </button>
              </div>

              {projectTab === 'documents' && (
                <button
                  onClick={() => setShowAssignDocModal(true)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition"
                >
                  <Plus className="w-3.5 h-3.5" /> Assign Doc
                </button>
              )}
            </div>
          </div>
        )}

        {/* Session Status Banner */}
        {isAuthenticated && user ? (
          <div className="px-6 py-2 bg-indigo-50/60 dark:bg-indigo-950/20 border-b border-indigo-100 dark:border-indigo-900/30 flex items-center justify-between text-xs text-indigo-700 dark:text-indigo-300">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
              <span>
                <strong>Private User Workspace:</strong> Encrypted & saved to your account (<strong>{user.email}</strong>). Strictly isolated from other users.
              </span>
            </div>
            <span className="text-[11px] text-indigo-600 dark:text-indigo-400 font-medium">
              Multi-Turn Memory Saved
            </span>
          </div>
        ) : (
          <div className="px-6 py-2.5 bg-amber-500/10 border-b border-amber-500/20 flex flex-wrap items-center justify-between gap-2 text-xs text-amber-700 dark:text-amber-300">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
              <span>
                <strong>Temporary Guest Session:</strong> Conversations exist only for this visit and will be deleted when you leave.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleClearGuestSession}
                className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-900 dark:text-amber-100 font-semibold text-[11px] transition cursor-pointer"
              >
                Clear Temporary Data
              </button>
              <button
                type="button"
                onClick={() => openAuthModal('signup')}
                className="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-[11px] transition shadow-xs cursor-pointer"
              >
                Sign Up to Save Permanently
              </button>
            </div>
          </div>
        )}

        {/* Isolation Banner */}
        <div className="px-6 py-2 bg-emerald-50/60 dark:bg-emerald-950/20 border-b border-emerald-100 dark:border-emerald-900/30 flex items-center justify-between text-xs text-emerald-800 dark:text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>
              <strong>Cross-Project Boundary Active:</strong> Queries only retrieve from the{' '}
              <strong>{projectDocs.length} documents</strong> assigned to this workspace.
            </span>
          </div>
          <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
            Multi-Turn Memory Enabled
          </span>
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="mx-6 mt-3 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* TAB 1: Chat Thread UI */}
        {projectTab === 'chat' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {!activeThread || activeThread.messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                    <MessageSquare className="w-6 h-6" />
                  </div>
                  <h4 className="font-bold text-sm text-slate-800 dark:text-slate-200">
                    {activeThread ? activeThread.title : 'Select a Thread'}
                  </h4>
                  <p className="text-xs text-slate-500">
                    Ask any question about the {projectDocs.length} documents in this workspace.
                    You can ask follow-ups naturally like <em>"Elaborate on point 2"</em> or <em>"Rewrite that in a table"</em>.
                  </p>
                </div>
              ) : (
                activeThread.messages.map((msg) => {
                  const isUser = msg.role === 'user';
                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1.5`}
                    >
                      <div className="flex items-center gap-2 text-[10px] text-slate-400 px-1 font-mono">
                        <span>{isUser ? 'You' : 'InsightForge Agent'}</span>
                        <span>•</span>
                        <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>

                      <div
                        className={`max-w-3xl p-5 rounded-2xl text-xs md:text-sm leading-relaxed ${isUser
                            ? 'bg-indigo-600 text-white rounded-br-none shadow-md shadow-indigo-600/10'
                            : 'bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-700/80 text-slate-800 dark:text-slate-100 rounded-bl-none space-y-4'
                          }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>

                        {/* If assistant: Interactive Chart */}
                        {msg.chart_data && (
                          <div className="pt-2">
                            <InteractiveChart chartData={msg.chart_data} />
                          </div>
                        )}

                        {/* If assistant: Audio Briefing & Citations */}
                        {!isUser && (
                          <div className="pt-3 border-t border-slate-200/60 dark:border-slate-700/60 space-y-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <AudioBriefing text={msg.content} topic={activeThread.title} />

                              {msg.is_grounded !== undefined && (
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1 ${msg.is_grounded
                                      ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300'
                                      : 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300'
                                    }`}
                                >
                                  <ShieldCheck className="w-3 h-3" />
                                  <span>{msg.is_grounded ? '100% Grounded' : 'Partial Grounding'}</span>
                                </span>
                              )}
                            </div>

                            {/* Citations */}
                            {msg.citations && msg.citations.length > 0 && (
                              <div className="space-y-1">
                                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                                  Verified Citations ({msg.citations.length}):
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {msg.citations.map((c, i) => (
                                    <button
                                      key={i}
                                      onClick={() =>
                                        c.document_id &&
                                        setViewerDoc({ id: c.document_id, name: c.source_filename })
                                      }
                                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/60 dark:border-indigo-900 text-indigo-700 dark:text-indigo-300 text-[10px] font-medium hover:underline"
                                    >
                                      <FileText className="w-2.5 h-2.5" />
                                      <span>
                                        {c.source_filename} (p.{c.page_number})
                                      </span>
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Follow-Up Chips */}
            {activeThread && activeThread.messages.length > 0 && (
              <div className="px-6 py-2 border-t border-slate-100 dark:border-slate-800 flex items-center gap-2 overflow-x-auto bg-slate-50/50 dark:bg-slate-900/50">
                <span className="text-[11px] text-slate-400 font-semibold shrink-0">Follow-up:</span>
                {QUICK_FOLLOWUPS.map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSendMessage(chip)}
                    disabled={isSendingMessage}
                    className="px-2.5 py-1 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-[11px] whitespace-nowrap hover:bg-indigo-50 hover:text-indigo-600 dark:hover:bg-indigo-950/50 transition cursor-pointer disabled:opacity-50"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            )}

            {/* Input Bar with Voice Input & Send */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="relative flex items-center"
              >
                <textarea
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  rows={2}
                  placeholder={`Ask a question or follow-up in '${activeProject?.name}'...`}
                  className="w-full pl-4 pr-32 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-xs md:text-sm text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none leading-relaxed"
                />

                <div className="absolute right-3 bottom-2.5 flex items-center gap-1.5">
                  <VoiceInputButton
                    onTranscript={(txt) => setInputQuery((prev) => (prev ? `${prev} ${txt}` : txt))}
                    disabled={isSendingMessage}
                  />

                  <button
                    type="submit"
                    disabled={isSendingMessage || !inputQuery.trim()}
                    className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold transition disabled:opacity-50 shadow-md shadow-indigo-600/20"
                  >
                    {isSendingMessage ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* TAB 2: Documents in Project UI */}
        {projectTab === 'documents' && (
          <div className="flex-1 p-6 overflow-y-auto space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-bold text-sm text-slate-800 dark:text-slate-100">
                  Documents Assigned to {activeProject?.name}
                </h4>
                <p className="text-xs text-slate-500">
                  Only these files will be searched when asking questions in this workspace collection.
                </p>
              </div>

              <button
                onClick={() => setShowAssignDocModal(true)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition"
              >
                <Plus className="w-3.5 h-3.5" /> Assign Document
              </button>
            </div>

            {projectDocs.length === 0 ? (
              <div className="p-12 text-center rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-800 space-y-2">
                <FileText className="w-8 h-8 text-slate-400 mx-auto" />
                <h5 className="font-bold text-xs text-slate-700 dark:text-slate-300">
                  No documents in this workspace collection yet.
                </h5>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Click 'Assign Document' to select files from your library, ensuring queries in this project stay 100% isolated.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {projectDocs.map((doc) => (
                  <div
                    key={doc.document_id}
                    className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 truncate">
                      <div className="p-2 rounded-xl bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div className="truncate">
                        <h5 className="font-bold text-xs text-slate-800 dark:text-slate-100 truncate">
                          {doc.filename}
                        </h5>
                        <p className="text-[11px] text-slate-400">
                          {doc.total_pages} pages • {doc.total_chunks} chunks
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setViewerDoc({ id: doc.document_id, name: doc.filename })}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
                        title="Preview Document"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleRemoveDocument(doc.document_id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950 transition"
                        title="Remove from project"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* MODAL 1: Create New Workspace Project */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-3xl p-6 border border-slate-200 dark:border-slate-800 shadow-2xl space-y-4 animate-in fade-in zoom-in-95">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Create New Workspace Collection
            </h3>
            <p className="text-xs text-slate-500">
              Create an isolated project so searches in this workspace never mix with other files.
            </p>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Collection Name
                </label>
                <input
                  type="text"
                  value={newProjName}
                  onChange={(e) => setNewProjName(e.target.value)}
                  placeholder="e.g. Legal Contracts & NDAs"
                  required
                  className="w-full px-3.5 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  value={newProjDesc}
                  onChange={(e) => setNewProjDesc(e.target.value)}
                  placeholder="What is this workspace dedicated to?"
                  rows={2}
                  className="w-full px-3.5 py-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewProjectModal(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newProjName.trim()}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  Create Collection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Assign Document to Workspace */}
      {showAssignDocModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-3xl p-6 border border-slate-200 dark:border-slate-800 shadow-2xl space-y-4 animate-in fade-in zoom-in-95">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Assign Document to {activeProject?.name}
            </h3>
            <p className="text-xs text-slate-500">
              Select an existing document from your library to add to this isolated workspace.
            </p>

            <div className="space-y-3">
              <select
                value={selectedDocToAssign}
                onChange={(e) => setSelectedDocToAssign(e.target.value)}
                className="w-full px-3.5 py-2.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">-- Choose a Document --</option>
                {unassignedDocs.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.filename} ({d.total_pages} pages)
                  </option>
                ))}
              </select>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowAssignDocModal(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssignDocument}
                  disabled={!selectedDocToAssign}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  Add to Workspace
                </button>
              </div>
            </div>
          </div>
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

