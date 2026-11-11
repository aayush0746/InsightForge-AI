import React, { useEffect, useState } from 'react';
import {
  FileText,
  BrainCircuit,
  ShieldCheck,
  Layers,
  ArrowRight,
  Upload,
  CheckCircle2,
  Clock,
  Sparkles
} from 'lucide-react';
import { MetricCard } from '../components/MetricCard';
import { api } from '../services/api';
import { SystemHealth, ResearchReportSummary } from '../types';

interface DashboardProps {
  setCurrentTab: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ setCurrentTab }) => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [reports, setReports] = useState<ResearchReportSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [healthData, reportsData] = await Promise.all([
          api.getHealth(),
          api.listReports()
        ]);
        setHealth(healthData);
        setReports(reportsData);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const totalReports = reports.length;
  const avgGrounding = reports.length > 0
    ? (reports.reduce((acc, r) => acc + r.grounding_score, 0) / reports.length).toFixed(1)
    : '100.0';

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Welcome Banner */}
      <div className="relative p-8 rounded-3xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white overflow-hidden shadow-xl">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-500/30 via-transparent to-transparent pointer-events-none" />
        <div className="max-w-2xl relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-200 text-xs font-medium mb-4 backdrop-blur-sm">
            <Sparkles className="w-3.5 h-3.5 text-indigo-300" />
            <span>Agentic Research & Decision Intelligence</span>
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight mb-3">
            Welcome to InsightForge AI
          </h2>
          <p className="text-indigo-100/90 text-sm leading-relaxed mb-6 font-normal">
            Upload PDFs, execute multi-agent deep research, rerank findings with neural CrossEncoders,
            and inspect fully grounded reports with verified page-level citations.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setCurrentTab('workspace')}
              className="px-5 py-2.5 rounded-xl bg-white text-indigo-900 font-semibold text-sm hover:bg-indigo-50 transition shadow-md flex items-center space-x-2"
            >
              <BrainCircuit className="w-4 h-4 text-indigo-600" />
              <span>Launch Research Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentTab('documents')}
              className="px-5 py-2.5 rounded-xl bg-indigo-700/60 hover:bg-indigo-700 text-white font-medium text-sm border border-indigo-500/40 transition flex items-center space-x-2"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Documents</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Indexed Documents"
          value={health?.total_indexed_documents ?? 0}
          subtitle="Ready for semantic query"
          icon={FileText}
          gradient="from-indigo-500/20 to-transparent"
        />
        <MetricCard
          title="Total Chunks"
          value={health?.total_chunks ?? 0}
          subtitle="Sentence & paragraph aware"
          icon={Layers}
          gradient="from-blue-500/20 to-transparent"
        />
        <MetricCard
          title="Research Reports"
          value={totalReports}
          subtitle="Full multi-agent workflows"
          icon={BrainCircuit}
          gradient="from-violet-500/20 to-transparent"
        />
        <MetricCard
          title="Avg Grounding Score"
          value={`${avgGrounding}%`}
          subtitle="Fact-checker verified"
          icon={ShieldCheck}
          gradient="from-emerald-500/20 to-transparent"
        />
      </div>

      {/* Main Grid: Architecture Status & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Architecture Engine Card */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs space-y-4">
          <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100 flex items-center justify-between">
            <span>RAG & Multi-Agent Stack</span>
            <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
              Operational
            </span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex justify-between items-center">
              <div>
                <p className="font-medium text-slate-800 dark:text-slate-200">LLM Reasoning Engine</p>
                <p className="text-slate-400 font-mono text-[11px] mt-0.5">Google Gemini 3.6 Flash</p>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex justify-between items-center">
              <div>
                <p className="font-medium text-slate-800 dark:text-slate-200">Neural Reranker</p>
                <p className="text-slate-400 font-mono text-[11px] mt-0.5">ms-marco-MiniLM-L-6-v2</p>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex justify-between items-center">
              <div>
                <p className="font-medium text-slate-800 dark:text-slate-200">Vector Embeddings</p>
                <p className="text-slate-400 font-mono text-[11px] mt-0.5">all-MiniLM-L6-v2 (ChromaDB)</p>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex justify-between items-center">
              <div>
                <p className="font-medium text-slate-800 dark:text-slate-200">Agentic Orchestration</p>
                <p className="text-slate-400 text-[11px] mt-0.5">Planner, Research, Analyst, Critic, Fact-Check, Synth</p>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
          </div>
        </div>

        {/* Recent Research Sessions */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Recent Research Inquiries
              </h3>
              <button
                onClick={() => setCurrentTab('reports')}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
              >
                View all reports
              </button>
            </div>

            {reports.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                <BrainCircuit className="w-8 h-8 mx-auto mb-2 opacity-40 text-slate-400" />
                <p>No research reports generated yet.</p>
                <p className="text-slate-500 mt-1">Ask a question in the Research Workspace to trigger the multi-agent pipeline.</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {reports.slice(0, 4).map((r) => (
                  <div
                    key={r.research_id}
                    onClick={() => setCurrentTab('reports')}
                    className="p-3.5 rounded-xl border border-slate-100 dark:border-slate-800 hover:border-slate-200 dark:hover:border-slate-700 bg-slate-50/50 dark:bg-slate-800/20 cursor-pointer transition flex items-center justify-between"
                  >
                    <div className="max-w-[70%]">
                      <p className="font-medium text-xs text-slate-800 dark:text-slate-200 truncate">
                        {r.question}
                      </p>
                      <div className="flex items-center space-x-3 text-[11px] text-slate-400 mt-1">
                        <span className="flex items-center gap-1 font-mono">
                          <Clock className="w-3 h-3" />
                          {new Date(r.created_at).toLocaleDateString()}
                        </span>
                        <span>{r.key_findings_count} findings</span>
                        <span>{r.citations_count} citations</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-mono text-xs font-semibold">
                        {r.grounding_score}% Grounded
                      </span>
                      <ArrowRight className="w-4 h-4 text-slate-400" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 mt-4 flex items-center justify-between text-xs text-slate-500">
            <span>Chroma Vector Store: <strong className="text-slate-700 dark:text-slate-300">Persistent</strong></span>
            <span>Hallucination Detection: <strong className="text-emerald-600 dark:text-emerald-400">Strict Grounding</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
};

