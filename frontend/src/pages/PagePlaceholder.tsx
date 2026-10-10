import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { DashboardIcon, LogoIcon } from '../components/common/Icons';

export const PagePlaceholder: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="max-w-3xl mx-auto py-12 px-6 text-center space-y-6">
      <div className="w-16 h-16 rounded-2xl bg-cyan-50 text-cyan-600 flex items-center justify-center mx-auto border border-cyan-200 shadow-2xs">
        <LogoIcon size={32} />
      </div>

      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
          Module Navigation Placeholder
        </h2>
        <p className="text-sm text-slate-500 max-w-md mx-auto">
          The route <code className="font-mono text-cyan-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 font-bold">{location.pathname}</code> is registered in ChemRAG but its interactive view is currently under development for an upcoming stage.
        </p>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 max-w-md mx-auto text-left space-y-3 shadow-sm">
        <div className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider">
          Available Scientific Modules
        </div>
        <ul className="text-xs text-slate-700 space-y-2 font-mono">
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <a href="/chat" className="hover:underline text-cyan-700 font-bold">/chat</a> — Research Chat Assistant
          </li>
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <a href="/documents" className="hover:underline text-cyan-700 font-bold">/documents</a> — Document Library
          </li>
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <a href="/jobs" className="hover:underline text-cyan-700 font-bold">/jobs</a> — Processing Pipeline
          </li>
          <li className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <a href="/settings" className="hover:underline text-cyan-700 font-bold">/settings</a> — System Settings & Diagnostics
          </li>
        </ul>
      </div>

      <div>
        <button
          onClick={() => navigate('/')}
          type="button"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition-colors shadow-sm"
        >
          <DashboardIcon size={16} />
          <span>Return to Workspace Overview</span>
        </button>
      </div>
    </div>
  );
};

export default PagePlaceholder;
