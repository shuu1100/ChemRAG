import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { DashboardIcon, LogoIcon } from '../components/common/Icons';

export const PagePlaceholder: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="max-w-3xl mx-auto py-12 px-6 text-center space-y-6">
      <div className="w-16 h-16 rounded-2xl bg-cyan-950 text-cyan-400 flex items-center justify-center mx-auto border border-cyan-800 shadow-md">
        <LogoIcon size={32} />
      </div>

      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Module Navigation Placeholder
        </h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          The route <code className="font-mono text-cyan-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">{location.pathname}</code> is registered in ChemRAG but its interactive view is currently under development for an upcoming stage.
        </p>
      </div>

      <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 max-w-md mx-auto text-left space-y-3 shadow-md">
        <div className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
          Available Scientific Modules
        </div>
        <ul className="text-xs text-slate-300 space-y-2 font-mono">
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <a href="/chat" className="hover:underline text-cyan-400 font-semibold">/chat</a> — Research Chat Assistant
          </li>
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <a href="/documents" className="hover:underline text-cyan-400 font-semibold">/documents</a> — Document Library
          </li>
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <a href="/jobs" className="hover:underline text-cyan-400 font-semibold">/jobs</a> — Processing Pipeline
          </li>
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <a href="/settings" className="hover:underline text-cyan-400 font-semibold">/settings</a> — System Settings & Diagnostics
          </li>
        </ul>
      </div>

      <div>
        <button
          onClick={() => navigate('/')}
          type="button"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 text-white text-xs font-semibold hover:from-cyan-500 hover:to-blue-500 transition-colors shadow-md border border-cyan-400/30"
        >
          <DashboardIcon size={16} />
          <span>Return to Workspace Overview</span>
        </button>
      </div>
    </div>
  );
};
