import React, { useState } from 'react';
import { AgentExecutionStep } from '../types';
import {
  Brain,
  Search,
  LineChart,
  ShieldAlert,
  CheckCircle2,
  FileCheck2,
  ChevronDown,
  ChevronRight,
  Clock
} from 'lucide-react';

interface AgentTimelineProps {
  steps: AgentExecutionStep[];
  currentAgent?: string;
}

const AGENT_ICONS: Record<string, React.ElementType> = {
  'Planner Agent': Brain,
  'Research Agent': Search,
  'Analyst Agent': LineChart,
  'Critic Agent': ShieldAlert,
  'Fact Checker Agent': CheckCircle2,
  'Synthesizer Agent': FileCheck2,
};

export const AgentTimeline: React.FC<AgentTimelineProps> = ({ steps, currentAgent }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const toggleExpand = (idx: number) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Agent Execution Pipeline
        </h4>
        <span className="text-[11px] text-slate-400">
          {steps.filter(s => s.status === 'completed').length} / 6 Completed
        </span>
      </div>

      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
        {steps.map((step, idx) => {
          const Icon = AGENT_ICONS[step.agent_name] || Brain;
          const isExpanded = expandedIndex === idx;
          const isCurrent = currentAgent === step.agent_name;

          return (
            <div key={idx} className="relative group">
              {/* Node Dot */}
              <div
                className={`absolute -left-6 top-1.5 w-5 h-5 rounded-full flex items-center justify-center border-2 bg-white dark:bg-slate-900 transition-all ${
                  step.status === 'completed'
                    ? 'border-emerald-500 text-emerald-500'
                    : isCurrent
                    ? 'border-indigo-600 text-indigo-600 animate-pulse'
                    : 'border-slate-300 dark:border-slate-700 text-slate-400'
                }`}
              >
                <Icon className="w-2.5 h-2.5" />
              </div>

              {/* Card */}
              <div
                onClick={() => toggleExpand(idx)}
                className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                  isCurrent
                    ? 'bg-indigo-50/50 dark:bg-indigo-950/30 border-indigo-200 dark:border-indigo-800'
                    : 'bg-white dark:bg-slate-900/60 border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {step.agent_name}
                    </span>
                    {step.status === 'completed' && (
                      <span className="px-1.5 py-0.2 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 rounded text-[10px] font-medium">
                        Done
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2 text-slate-400">
                    <span className="flex items-center gap-1 font-mono text-[11px]">
                      <Clock className="w-3 h-3" />
                      {step.execution_time_seconds.toFixed(2)}s
                    </span>
                    {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  </div>
                </div>

                <p className="text-slate-600 dark:text-slate-300 font-medium">
                  {step.title}
                </p>
                <p className="text-slate-400 mt-0.5 text-[11px]">
                  {step.details}
                </p>

                {/* Collapsible raw data */}
                {isExpanded && step.data && (
                  <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <pre className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/80 text-[10px] font-mono text-slate-700 dark:text-slate-300 overflow-x-auto max-h-48">
                      {JSON.stringify(step.data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

