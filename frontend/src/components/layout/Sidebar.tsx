import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/chat', label: 'ChemRAG Chat', icon: '💬' },
  { path: '/documents', label: 'Documents', icon: '📄' },
  { path: '/viewer', label: 'PDF Viewer', icon: '👁️' },
  { path: '/search', label: 'Search', icon: '🔍' },
  { path: '/chemical', label: 'Chemical Explorer', icon: '🧪' },
  { path: '/experiments', label: 'Experiments', icon: '🧪' },
  { path: '/jobs', label: 'Jobs', icon: '⚙️' },
  { path: '/evaluation', label: 'Evaluation', icon: '📈' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between py-4 shrink-0">
      <nav className="space-y-1 px-3">
        <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">
          Research Modules
        </div>

        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-950 to-blue-950 text-cyan-400 border border-cyan-800/80 shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer Info */}
      <div className="px-6 py-3 border-t border-slate-800 text-[11px] text-slate-500 font-mono">
        <div>Env: <span className="text-slate-400">development</span></div>
        <div>Engine: <span className="text-cyan-400">pgvector + RDKit</span></div>
      </div>
    </aside>
  );
};
