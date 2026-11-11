import React, { useState, useEffect } from 'react';
import {
  Scale,
  Play,
  Sparkles,
  Trophy,
  CheckCircle2,
  Clock,
  Layers,
  BarChart3,
  History,
  FileCode2,
  ChevronRight
} from 'lucide-react';
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend
} from 'recharts';
import { api } from '../services/api';
import {
  PromptTemplate,
  EvaluationRunRecord,
  EvaluationHistorySummary
} from '../types';

export const Evaluation: React.FC = () => {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [history, setHistory] = useState<EvaluationHistorySummary[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState(
    'How can a final-year computer science student prepare for a GenAI job?'
  );

  // Prompts under test
  const [prompt1Name, setPrompt1Name] = useState('Basic Prompt');
  const [prompt1Template, setPrompt1Template] = useState('{question}');

  const [prompt2Name, setPrompt2Name] = useState('Advanced Prompt');
  const [prompt2Template, setPrompt2Template] = useState(`You are an expert GenAI Architect and Career Consultant.
Analyze the following user question thoroughly:

{question}

Provide an actionable, comprehensive, and well-structured roadmap.
Rules:
- Prioritize essential fundamentals (CS, ML, RAG, Agents).
- Distinguish core foundational knowledge from optional advanced topics.
- Provide concrete, step-by-step guidance.
- Avoid repetitive or vague advice.`);

  const [isRunning, setIsRunning] = useState(false);
  const [activeRecord, setActiveRecord] = useState<EvaluationRunRecord | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        const [tmpls, hist] = await Promise.all([
          api.getTemplates(),
          api.getEvaluationHistory()
        ]);
        setTemplates(tmpls);
        setHistory(hist);
      } catch (err) {
        console.error('Failed to load evaluation metadata:', err);
      }
    }
    loadInitial();
  }, []);

  const handleRunEvaluation = async () => {
    if (!selectedQuestion.trim() || isRunning) return;
    setIsRunning(true);
    setErrorMsg(null);

    const promptsPayload = {
      [prompt1Name]: prompt1Template,
      [prompt2Name]: prompt2Template,
    };

    try {
      const record = await api.evaluatePrompts({
        question: selectedQuestion.trim(),
        prompts: promptsPayload,
        save_to_history: true
      });
      setActiveRecord(record);
      // Refresh history list
      const hist = await api.getEvaluationHistory();
      setHistory(hist);
    } catch (err: any) {
      setErrorMsg(err.message || 'Prompt evaluation failed.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleSelectHistoryRun = async (runId: string) => {
    try {
      const run = await api.getEvaluationRun(runId);
      setActiveRecord(run);
      if (run) {
        setSelectedQuestion(run.question);
      }
    } catch (err) {
      console.error('Failed to fetch run:', err);
    }
  };

  // Prepare radar/bar chart data if activeRecord exists
  const chartData = activeRecord
    ? [
        {
          metric: 'Relevance',
          ...Object.fromEntries(
            Object.entries(activeRecord.results).map(([name, r]) => [name, r.metrics.relevance])
          )
        },
        {
          metric: 'Accuracy',
          ...Object.fromEntries(
            Object.entries(activeRecord.results).map(([name, r]) => [name, r.metrics.accuracy])
          )
        },
        {
          metric: 'Clarity',
          ...Object.fromEntries(
            Object.entries(activeRecord.results).map(([name, r]) => [name, r.metrics.clarity])
          )
        },
        {
          metric: 'Completeness',
          ...Object.fromEntries(
            Object.entries(activeRecord.results).map(([name, r]) => [name, r.metrics.completeness])
          )
        },
        {
          metric: 'Actionability',
          ...Object.fromEntries(
            Object.entries(activeRecord.results).map(([name, r]) => [name, r.metrics.actionability])
          )
        },
        {
          metric: 'Faithfulness',
          ...Object.fromEntries(
            Object.entries(activeRecord.results).map(([name, r]) => [name, r.metrics.faithfulness])
          )
        },
      ]
    : [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-in fade-in duration-200">
      {/* Test Question & Benchmark Controls */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Scale className="w-4 h-4 text-indigo-600" />
              LLM-as-a-Judge Prompt Engineering Benchmark
            </h3>
            <p className="text-xs text-slate-500">
              Strict multi-dimensional scoring across 6 independent evaluation metrics
            </p>
          </div>

          <button
            onClick={handleRunEvaluation}
            disabled={isRunning || !selectedQuestion.trim()}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 transition shadow-md shadow-indigo-600/20 cursor-pointer"
          >
            {isRunning ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Running Judge...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Evaluate Prompts</span>
              </>
            )}
          </button>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            Benchmark Test Question:
          </label>
          <input
            type="text"
            value={selectedQuestion}
            onChange={(e) => setSelectedQuestion(e.target.value)}
            className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Prompt Variant 1 & Variant 2 Side-by-Side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Variant A */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <input
                type="text"
                value={prompt1Name}
                onChange={(e) => setPrompt1Name(e.target.value)}
                className="font-bold text-xs bg-transparent border-b border-transparent hover:border-slate-300 dark:hover:border-slate-700 focus:outline-hidden text-indigo-600 dark:text-indigo-400"
              />
              <span className="text-[10px] text-slate-400 font-mono">Baseline</span>
            </div>
            <textarea
              value={prompt1Template}
              onChange={(e) => setPrompt1Template(e.target.value)}
              rows={5}
              className="w-full p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-800 dark:text-slate-200 resize-none focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Variant B */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <input
                type="text"
                value={prompt2Name}
                onChange={(e) => setPrompt2Name(e.target.value)}
                className="font-bold text-xs bg-transparent border-b border-transparent hover:border-slate-300 dark:hover:border-slate-700 focus:outline-hidden text-indigo-600 dark:text-indigo-400"
              />
              <span className="text-[10px] text-slate-400 font-mono">Optimized</span>
            </div>
            <textarea
              value={prompt2Template}
              onChange={(e) => setPrompt2Template(e.target.value)}
              rows={5}
              className="w-full p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-800 dark:text-slate-200 resize-none focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* Error state */}
      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs">
          {errorMsg}
        </div>
      )}

      {/* Active Evaluation Comparison Display */}
      {activeRecord && (
        <div className="space-y-6">
          {/* Winner Card Banner */}
          <div className="p-6 rounded-3xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white shadow-lg flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-2xl bg-amber-400/20 text-amber-300 flex items-center justify-center border border-amber-300/30">
                <Trophy className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[11px] uppercase tracking-wider text-indigo-200 font-semibold">
                  Evaluator Recommendation
                </span>
                <h3 className="text-xl font-extrabold text-white">
                  Best Prompt: {activeRecord.best_prompt_name}
                </h3>
                <p className="text-xs text-indigo-200/80 mt-0.5">
                  Achieved highest overall quality score across relevance, actionability, and accuracy.
                </p>
              </div>
            </div>
            <div className="text-right">
              <span className="text-3xl font-black text-amber-300 font-mono">
                {activeRecord.results[activeRecord.best_prompt_name]?.metrics.overall.toFixed(1)}
              </span>
              <span className="text-xs text-indigo-200 block font-mono">/ 10 Overall</span>
            </div>
          </div>

          {/* Radar / Bar Comparison Chart & Metrics Table */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Radar Visualizer */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Multi-Dimensional Metric Radar
              </h4>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={chartData}>
                    <PolarGrid stroke="#94a3b8" strokeOpacity={0.2} />
                    <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <PolarRadiusAxis domain={[0, 10]} stroke="#94a3b8" strokeOpacity={0.2} />
                    <Radar
                      name={prompt1Name}
                      dataKey={prompt1Name}
                      stroke="#818cf8"
                      fill="#818cf8"
                      fillOpacity={0.25}
                    />
                    <Radar
                      name={prompt2Name}
                      dataKey={prompt2Name}
                      stroke="#10b981"
                      fill="#10b981"
                      fillOpacity={0.35}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Metrics Breakdown Table */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Score Comparison (1 to 10)
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400">
                      <th className="pb-2 font-semibold">Metric</th>
                      {Object.keys(activeRecord.results).map((name) => (
                        <th key={name} className="pb-2 font-semibold text-center">{name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                    {['relevance', 'accuracy', 'clarity', 'completeness', 'actionability', 'faithfulness', 'overall'].map((m) => (
                      <tr key={m}>
                        <td className="py-2.5 font-sans font-medium capitalize text-slate-700 dark:text-slate-300">
                          {m}
                        </td>
                        {Object.values(activeRecord.results).map((res, i) => (
                          <td key={i} className="py-2.5 text-center font-bold text-slate-900 dark:text-slate-100">
                            {/* @ts-ignore */}
                            {res.metrics[m]?.toFixed ? res.metrics[m].toFixed(1) : res.metrics[m]}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Qualitative Feedback Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Object.entries(activeRecord.results).map(([name, res]) => (
              <div
                key={name}
                className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-3"
              >
                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                  <h4 className="font-bold text-xs text-indigo-600 dark:text-indigo-400">{name}</h4>
                  <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
                    Overall: {res.metrics.overall.toFixed(1)} / 10
                  </span>
                </div>
                <div className="space-y-2 text-xs">
                  <p className="text-slate-500 font-semibold uppercase text-[10px]">Evaluator Feedback:</p>
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-800/30 p-3 rounded-xl border border-slate-100 dark:border-slate-800">
                    {res.metrics.feedback}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History Log */}
      {history.length > 0 && (
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <History className="w-4 h-4 text-slate-400" />
              Past Evaluation Runs ({history.length})
            </h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {history.map((h) => (
              <button
                key={h.run_id}
                onClick={() => handleSelectHistoryRun(h.run_id)}
                className="p-3.5 rounded-xl border border-slate-100 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 bg-slate-50/50 dark:bg-slate-800/30 text-left transition cursor-pointer"
              >
                <p className="font-medium text-xs text-slate-800 dark:text-slate-200 truncate">{h.question}</p>
                <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 font-mono">
                  <span>{new Date(h.timestamp).toLocaleDateString()}</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-bold">Best: {h.best_prompt_name}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

