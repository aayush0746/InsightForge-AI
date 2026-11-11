import React from 'react';
import {
  LayoutDashboard,
  BrainCircuit,
  FileText,
  FileSearch,
  Scale,
  Settings,
  Sparkles,
  Database,
  GitCompare,
  FolderKanban,
  LogIn,
  LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { GoogleIcon } from './AuthModal';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  documentCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  setCurrentTab,
  documentCount,
}) => {
  const { user, isAuthenticated, openAuthModal, signOut } = useAuth();
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects', label: 'Projects & Workspaces', icon: FolderKanban, badge: 'Enterprise' },
    { id: 'workspace', label: 'Research Workspace', icon: BrainCircuit, badge: 'Agentic' },
    { id: 'documents', label: 'Document Library', icon: FileText, count: documentCount },
    { id: 'compare', label: 'Document Diff', icon: GitCompare, badge: 'Matrix' },
    { id: 'reports', label: 'Research Reports', icon: FileSearch },
    { id: 'evaluation', label: 'Prompt Evaluation', icon: Scale },
    { id: 'settings', label: 'Settings & Tuning', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col justify-between shrink-0 select-none transition-colors duration-200">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-500 bg-clip-text text-transparent">
              InsightForge AI
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">Research Intelligence</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                  ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 font-semibold shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
                    {item.badge}
                  </span>
                )}
                {item.count !== undefined && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Auth Profile Card */}
      <div className="px-3 pt-2">
        {isAuthenticated && user ? (
          <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5 truncate">
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  className="w-8 h-8 rounded-full object-cover border border-slate-300 dark:border-slate-600 shrink-0"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
                  {user.name.charAt(0).toUpperCase()}
                </div>
              )}
              <div className="truncate">
                <div className="flex items-center gap-1">
                  <span className="font-bold text-xs text-slate-800 dark:text-slate-100 truncate">
                    {user.name}
                  </span>
                  {user.provider === 'google' && (
                    <GoogleIcon className="w-3 h-3 shrink-0" />
                  )}
                </div>
                <p className="text-[10px] text-slate-400 truncate">{user.email}</p>
              </div>
            </div>

            <button
              onClick={() => signOut()}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition shrink-0 ml-1"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => openAuthModal('signin')}
            className="w-full flex items-center justify-center gap-2 p-2.5 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 border border-indigo-200/70 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-xs font-semibold transition cursor-pointer"
          >
            <GoogleIcon className="w-4 h-4" />
            <span>Sign in with Google</span>
          </button>
        )}
      </div>

      {/* System Status Footer */}
      <div className="p-4 m-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/60 dark:border-slate-800 text-xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-medium text-slate-700 dark:text-slate-300">System Ready</span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">v1.0</span>
        </div>
        <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1"><Database className="w-3 h-3" /> ChromaDB</span>
          <span className="text-emerald-600 dark:text-emerald-400 font-medium">Active</span>
        </div>
      </div>
    </aside>
  );
};

