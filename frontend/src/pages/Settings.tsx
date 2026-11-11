import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  Save,
  CheckCircle2,
  Cpu,
  Database,
  Sliders,
  Layers,
  Sparkles,
  Info
} from 'lucide-react';
import { api } from '../services/api';
import { SystemSettings, SystemHealth } from '../types';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    async function fetchConfig() {
      try {
        const [settingsData, healthData] = await Promise.all([
          api.getSettings(),
          api.getHealth()
        ]);
        setSettings(settingsData);
        setHealth(healthData);
      } catch (err) {
        console.error('Failed to load settings:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchConfig();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (loading || !settings) {
    return <div className="p-8 text-center text-xs text-slate-400">Loading settings...</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-in fade-in duration-200">
      <form onSubmit={handleSave} className="space-y-6">
        {/* Model Configuration Card */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-5">
          <div className="flex items-center space-x-2 pb-3 border-b border-slate-100 dark:border-slate-800">
            <Cpu className="w-4 h-4 text-indigo-600" />
            <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
              Reasoning Engine & Model Configuration
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Primary Gemini Model:
              </label>
              <select
                value={settings.model_name}
                onChange={(e) => setSettings({ ...settings, model_name: e.target.value })}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 font-mono"
              >
                {settings.available_models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              <p className="text-[11px] text-slate-400 mt-1">
                Utilizes Google GenAI interactions and reasoning API.
              </p>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Temperature:
                </label>
                <span className="font-mono text-xs font-bold text-indigo-600">{settings.temperature}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settings.temperature}
                onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Lower values (0.1 - 0.3) provide strict factuality and citation precision.
              </p>
            </div>
          </div>
        </div>

        {/* Advanced RAG Pipeline Tuning */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-5">
          <div className="flex items-center space-x-2 pb-3 border-b border-slate-100 dark:border-slate-800">
            <Sliders className="w-4 h-4 text-indigo-600" />
            <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
              Advanced RAG & Neural Reranker Tuning
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Chunk Size */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Chunk Size (Words):
                </label>
                <span className="font-mono text-xs font-bold text-indigo-600">{settings.chunk_size} words</span>
              </div>
              <input
                type="range"
                min="40"
                max="180"
                step="10"
                value={settings.chunk_size}
                onChange={(e) => setSettings({ ...settings, chunk_size: parseInt(e.target.value) })}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Target words per chunk before boundary break.
              </p>
            </div>

            {/* Overlap */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Chunk Overlap (Words):
                </label>
                <span className="font-mono text-xs font-bold text-indigo-600">{settings.chunk_overlap} words</span>
              </div>
              <input
                type="range"
                min="5"
                max="40"
                step="5"
                value={settings.chunk_overlap}
                onChange={(e) => setSettings({ ...settings, chunk_overlap: parseInt(e.target.value) })}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Words shared between consecutive chunks to prevent boundary cutoff.
              </p>
            </div>

            {/* Retrieval Top K Candidates */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Candidate Chunks (Top K):
                </label>
                <span className="font-mono text-xs font-bold text-indigo-600">{settings.retrieval_top_k} candidates</span>
              </div>
              <input
                type="range"
                min="4"
                max="25"
                step="1"
                value={settings.retrieval_top_k}
                onChange={(e) => setSettings({ ...settings, retrieval_top_k: parseInt(e.target.value) })}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Number of chunks fetched by hybrid search prior to reranking.
              </p>
            </div>

            {/* CrossEncoder Rerank Top N */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Reranked Final Chunks (Top N):
                </label>
                <span className="font-mono text-xs font-bold text-indigo-600">{settings.rerank_top_n} chunks</span>
              </div>
              <input
                type="range"
                min="2"
                max="8"
                step="1"
                value={settings.rerank_top_n}
                onChange={(e) => setSettings({ ...settings, rerank_top_n: parseInt(e.target.value) })}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Top scored chunks retained after CrossEncoder neural reranking.
              </p>
            </div>

            {/* Hybrid Alpha */}
            <div className="md:col-span-2">
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Hybrid Search Alpha (Dense Semantic vs Keyword):
                </label>
                <span className="font-mono text-xs font-bold text-indigo-600">
                  {Math.round(settings.hybrid_alpha * 100)}% Dense / {Math.round((1 - settings.hybrid_alpha) * 100)}% BM25
                </span>
              </div>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={settings.hybrid_alpha}
                onChange={(e) => setSettings({ ...settings, hybrid_alpha: parseFloat(e.target.value) })}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* System Diagnostics & Information */}
        {health && (
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-3 text-xs">
            <h4 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Database className="w-4 h-4 text-emerald-500" />
              Vector Database & Model Diagnostics
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-400 block text-[10px]">Chroma Status</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400 capitalize">{health.chroma_db_status}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-400 block text-[10px]">Indexed Chunks</span>
                <span className="font-semibold font-mono text-slate-900 dark:text-slate-100">{health.total_chunks}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-400 block text-[10px]">Embedding Model</span>
                <span className="font-semibold font-mono text-slate-900 dark:text-slate-100 text-[11px] truncate block">{health.embedding_model}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800">
                <span className="text-slate-400 block text-[10px]">CrossEncoder</span>
                <span className="font-semibold font-mono text-slate-900 dark:text-slate-100 text-[11px] truncate block">{health.cross_encoder_model}</span>
              </div>
            </div>
          </div>
        )}

        {/* Save Bar */}
        <div className="flex items-center justify-between pt-2">
          {saveSuccess && (
            <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4" />
              <span>Settings updated successfully!</span>
            </div>
          )}
          {!saveSuccess && <div />}

          <button
            type="submit"
            disabled={isSaving}
            className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 transition shadow-md shadow-indigo-600/20 cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{isSaving ? 'Saving...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

