import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { Workspace } from './pages/Workspace';
import { Documents } from './pages/Documents';
import { DocumentCompare } from './pages/DocumentCompare';
import { Reports } from './pages/Reports';
import { Evaluation } from './pages/Evaluation';
import { Settings } from './pages/Settings';
import { AuthProvider } from './context/AuthContext';
import { AuthModal } from './components/AuthModal';
import { api } from './services/api';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [isDark, setIsDark] = useState<boolean>(() => {
    return localStorage.getItem('theme') === 'dark';
  });
  const [documentCount, setDocumentCount] = useState<number>(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const refreshGlobalData = async () => {
    setIsRefreshing(true);
    try {
      const res = await api.listDocuments();
      setDocumentCount(res.total_count);
    } catch (err) {
      console.error('Failed to refresh data:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    refreshGlobalData();
  }, []);

  const toggleTheme = () => setIsDark(prev => !prev);

  const getPageInfo = () => {
    switch (currentTab) {
      case 'dashboard':
        return {
          title: 'System Intelligence Dashboard',
          subtitle: 'Real-time overview of document ingestion, agent runs, and vector store metrics'
        };
      case 'projects':
        return {
          title: 'Workspace Projects & Follow-Up Threading',
          subtitle: 'Isolated collections ensuring searches never mix, with multi-turn conversational memory'
        };
      case 'workspace':
        return {
          title: 'AI Research Workspace',
          subtitle: 'Interactive inquiry console with Fast Grounded RAG & Multi-Agent Deep Research'
        };
      case 'documents':
        return {
          title: 'Document Library',
          subtitle: 'Multi-PDF upload, sentence & paragraph chunking, and persistent ChromaDB index'
        };
      case 'compare':
        return {
          title: 'Document Diff & Comparison Matrix',
          subtitle: 'Side-by-side delta analysis, added/removed clauses, and rule liability shifts'
        };
      case 'reports':
        return {
          title: 'Research Reports',
          subtitle: 'Publication-grade analytical syntheses, verified findings, and citations'
        };
      case 'evaluation':
        return {
          title: 'Prompt Evaluation Studio',
          subtitle: 'LLM-as-a-Judge benchmarking across 6 rigorous quality dimensions'
        };
      case 'settings':
        return {
          title: 'Settings & Model Tuning',
          subtitle: 'Configure reasoning parameters, chunk size, overlap, and CrossEncoder thresholds'
        };
      default:
        return { title: 'InsightForge AI', subtitle: 'Agentic Research Platform' };
    }
  };

  const pageInfo = getPageInfo();

  return (
    <AuthProvider>
      <div className="flex h-screen bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100 overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          currentTab={currentTab}
          setCurrentTab={setCurrentTab}
          documentCount={documentCount}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <Header
            title={pageInfo.title}
            subtitle={pageInfo.subtitle}
            isDark={isDark}
            toggleTheme={toggleTheme}
            onRefresh={refreshGlobalData}
            isRefreshing={isRefreshing}
          />

          <main className="flex-1 overflow-y-auto p-8">
            {currentTab === 'dashboard' && <Dashboard setCurrentTab={setCurrentTab} />}
            {currentTab === 'projects' && <Projects />}
            {currentTab === 'workspace' && <Workspace />}
            {currentTab === 'documents' && <Documents />}
            {currentTab === 'compare' && <DocumentCompare />}
            {currentTab === 'reports' && <Reports />}
            {currentTab === 'evaluation' && <Evaluation />}
            {currentTab === 'settings' && <Settings />}
          </main>
        </div>

        {/* Global Google & Email Authentication Modal */}
        <AuthModal />
      </div>
    </AuthProvider>
  );
}

export default App;
