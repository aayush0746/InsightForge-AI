import React, { useState, useEffect } from 'react';
import {
  FileSearch,
  Printer,
  Copy,
  Check,
  ShieldCheck,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react';
import { api } from '../services/api';
import { ResearchReport, ResearchReportSummary } from '../types';
import { useAuth } from '../context/AuthContext';
import { CitationBadge } from '../components/CitationBadge';
import { AgentTimeline } from '../components/AgentTimeline';
import { AudioBriefing } from '../components/AudioBriefing';
import { InteractiveChart } from '../components/InteractiveChart';

export const Reports: React.FC = () => {
  const { user } = useAuth();
  const [reportsList, setReportsList] = useState<ResearchReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [currentReport, setCurrentReport] = useState<ResearchReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const loadSummaries = async () => {
    try {
      setLoading(true);
      const summaries = await api.listReports();
      setReportsList(summaries);
      if (summaries.length > 0) {
        setSelectedReportId(summaries[0].research_id);
      } else {
        setSelectedReportId(null);
        setCurrentReport(null);
      }
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummaries();
  }, [user]);

  useEffect(() => {
    const handleAuthChange = () => {
      loadSummaries();
    };
    window.addEventListener('insightforge-auth-change', handleAuthChange);
    return () => window.removeEventListener('insightforge-auth-change', handleAuthChange);
  }, []);

  useEffect(() => {
    if (!selectedReportId) return;
    async function loadReport() {
      try {
        const rep = await api.getReport(selectedReportId!);
        setCurrentReport(rep);
      } catch (err) {
        console.error('Failed to load full report:', err);
      }
    }
    loadReport();
  }, [selectedReportId]);

  const generateMarkdownContent = (report: ResearchReport) => {
    return `# Research Report: ${report.question}
**Report ID**: ${report.research_id}
**Date**: ${new Date(report.created_at).toLocaleString()}
**Grounding Score**: ${report.grounding_score}%

---

## 1. Executive Summary
${report.executive_summary}

## 2. Research Methodology
${report.methodology}

## 3. Key Findings
${report.key_findings.map((f) => `- ${f}`).join('\n')}

## 4. Evidence Analysis
${report.evidence_analysis}

## 5. Analytical Interpretations
${report.ai_interpretations.map((i) => `- ${i}`).join('\n')}

## 6. Risks & Limitations
${report.risks_and_limitations.map((r) => `- ${r}`).join('\n')}

## 7. Recommendations
${report.recommendations.map((r) => `- ${r}`).join('\n')}

## 8. Sources & Citations
${report.citations.map((c, i) => `[${i + 1}] ${c.source_filename} (Page ${c.page_number}) - "${c.snippet}"`).join('\n\n')}
`;
  };

  const handleCopyMarkdown = () => {
    if (!currentReport) return;
    const md = generateMarkdownContent(currentReport);
    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    if (!currentReport) return;
    const md = generateMarkdownContent(currentReport);
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Report_${currentReport.research_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-in fade-in duration-200">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Reports Sidebar (1 col) */}
        <div className="p-4 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-3 h-fit">
          <div className="pb-2 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <h3 className="font-semibold text-xs uppercase tracking-wider text-slate-500">
              Reports Library
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">
              {reportsList.length}
            </span>
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading reports...</div>
          ) : reportsList.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No reports yet. Ask a question in the Workspace to generate one!
            </div>
          ) : (
            <div className="space-y-1.5 max-h-[70vh] overflow-y-auto">
              {reportsList.map((r) => (
                <button
                  key={r.research_id}
                  onClick={() => setSelectedReportId(r.research_id)}
                  className={`w-full text-left p-3 rounded-xl border text-xs transition ${selectedReportId === r.research_id
                    ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800 text-indigo-900 dark:text-indigo-200 font-semibold'
                    : 'border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/40 text-slate-700 dark:text-slate-300'
                    }`}
                >
                  <p className="line-clamp-2 leading-snug">{r.question}</p>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2">
                    <span className="font-mono">{new Date(r.created_at).toLocaleDateString()}</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                      {r.grounding_score}% Grounded
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detailed Report View (3 cols) */}
        <div className="lg:col-span-3">
          {currentReport ? (
            <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-6">
              {/* Header Action Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-5 border-b border-slate-100 dark:border-slate-800">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 text-xs font-mono font-bold">
                      {currentReport.research_id}
                    </span>
                    <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3" />
                      {new Date(currentReport.created_at).toLocaleString()}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-2 leading-snug">
                    {currentReport.question}
                  </h2>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {/* Audio Briefing Podcast Studio */}
                  <AudioBriefing
                    text={currentReport.executive_summary}
                    title="Executive Audio Briefing"
                    topic={currentReport.question}
                  />

                  <button
                    onClick={handleCopyMarkdown}
                    className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium flex items-center space-x-1.5 transition"
                    title="Copy Markdown"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                    <span>{copied ? 'Copied!' : 'Copy'}</span>
                  </button>

                  <button
                    onClick={handleDownloadMarkdown}
                    className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium flex items-center space-x-1.5 transition"
                    title="Download Markdown Report"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download MD</span>
                  </button>

                  <button
                    onClick={handlePrint}
                    className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-medium flex items-center space-x-1.5 transition"
                    title="Print or Save as PDF"
                  >
                    <Printer className="w-4 h-4" />
                    <span>Print PDF</span>
                  </button>
                </div>
              </div>

              {/* Verified Grounding Banner */}
              <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-900/40 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-xl bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
                      Fact-Checker Grounding Score: {currentReport.grounding_score}%
                    </h4>
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-300/80">
                      Evaluated by multi-agent audit across {currentReport.citations.length} retrieved
                      document chunks.
                    </p>
                  </div>
                </div>
              </div>

              {/* 1. Executive Summary */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  1. Executive Summary
                </h4>
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {currentReport.executive_summary}
                </div>
              </div>

              {/* Interactive Chart */}
              {currentReport.chart_data && (
                <InteractiveChart chartData={currentReport.chart_data} />
              )}

              {/* 2. Research Methodology */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  2. Research Methodology
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {currentReport.methodology}
                </p>
              </div>

              {/* 3. Key Findings */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  3. Key Findings (Document Backed)
                </h4>
                <div className="space-y-2">
                  {currentReport.key_findings.map((kf, i) => (
                    <div
                      key={i}
                      className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/30 border border-slate-100 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 flex items-start space-x-3"
                    >
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">{kf}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 4. Evidence Analysis */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  4. In-Depth Evidence Synthesis
                </h4>
                <div className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {currentReport.evidence_analysis}
                </div>
              </div>

              {/* 5. Risks & Limitations */}
              {currentReport.risks_and_limitations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    5. Risks, Limitations & Gaps
                  </h4>
                  <div className="space-y-1.5">
                    {currentReport.risks_and_limitations.map((risk, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/40 text-xs text-amber-900 dark:text-amber-200"
                      >
                        {risk}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 6. Recommendations */}
              {currentReport.recommendations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                    <Lightbulb className="w-3.5 h-3.5" />
                    6. Actionable Recommendations
                  </h4>
                  <div className="space-y-1.5">
                    {currentReport.recommendations.map((rec, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 text-xs text-emerald-950 dark:text-emerald-200 flex items-start space-x-2"
                      >
                        <ChevronRight className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 7. Citations & Page References */}
              <div className="space-y-3 pt-4 border-t border-slate-100 dark:border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  7. Verified Source References ({currentReport.citations.length})
                </h4>
                <div className="flex flex-wrap gap-2">
                  {currentReport.citations.map((c, i) => (
                    <CitationBadge key={i} citation={c} index={i} />
                  ))}
                </div>
              </div>

              {/* 8. Multi-Agent Audit Steps */}
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                <AgentTimeline steps={currentReport.agent_steps} />
              </div>
            </div>
          ) : (
            <div className="p-12 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-center text-slate-400 text-xs">
              Select a research report from the left panel to inspect details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
