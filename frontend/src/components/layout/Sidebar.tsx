import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  ChatIcon,
  ChemicalIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DashboardIcon,
  DocumentsIcon,
  EvaluationIcon,
  ExperimentsIcon,
  JobsIcon,
  LogoIcon,
  SearchIcon,
  SettingsIcon,
  ViewerIcon,
} from '../common/Icons';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onMobileClose?: () => void;
}

interface NavItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: 'RESEARCH WORKSPACE',
    items: [
      { path: '/chat', label: 'Research Chat', icon: ChatIcon, badge: 'RAG' },
      { path: '/documents', label: 'Document Library', icon: DocumentsIcon },
      { path: '/', label: 'Workspace Overview', icon: DashboardIcon },
    ],
  },
  {
    title: 'ANALYSIS & DISCOVERY',
    items: [
      { path: '/chemical', label: 'Chemical Explorer', icon: ChemicalIcon },
      { path: '/search', label: 'Hybrid Search', icon: SearchIcon },
      { path: '/viewer', label: 'PDF & Citation Viewer', icon: ViewerIcon },
      { path: '/experiments', label: 'Experimental Records', icon: ExperimentsIcon },
    ],
  },
  {
    title: 'PIPELINE & SYSTEM',
    items: [
      { path: '/jobs', label: 'Processing Pipeline', icon: JobsIcon },
      { path: '/evaluation', label: 'Retrieval Metrics', icon: EvaluationIcon },
      { path: '/settings', label: 'Settings & Diagnostics', icon: SettingsIcon },
    ],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, onToggleCollapse, onMobileClose }) => {
  return (
    <aside
      className={`sidebar-transition h-full bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0 select-none text-slate-100 ${
        isCollapsed ? 'w-20' : 'w-64'
      }`}
      aria-label="Sidebar Navigation"
    >
      {/* Top Branding Section */}
      <div className="flex flex-col flex-1 overflow-y-auto no-scrollbar">
        <div className={`p-4 flex items-center border-b border-slate-800/80 ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-600 flex items-center justify-center text-white shadow-md shadow-cyan-950/40 ring-1 ring-cyan-400/40 shrink-0">
              <LogoIcon size={20} />
            </div>
            {!isCollapsed && (
              <div className="truncate">
                <div className="flex items-center gap-2">
                  <span className="text-base font-bold tracking-tight text-white">ChemRAG</span>
                  <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 bg-cyan-950 text-cyan-300 border border-cyan-800/80 rounded">
                    v0.1.0
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 font-sans leading-none mt-0.5 truncate">
                  Scientific Research Workspace
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Sections */}
        <nav className="p-3 space-y-5 flex-1">
          {navSections.map((section, idx) => (
            <div key={idx} className="space-y-1">
              {!isCollapsed ? (
                <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">
                  {section.title}
                </div>
              ) : (
                <div className="w-full h-px bg-slate-800/80 my-2" />
              )}

              {section.items.map((item) => {
                const IconComponent = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    onClick={onMobileClose}
                    title={isCollapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-lg font-medium transition-all group ${
                        isCollapsed ? 'px-3 py-3 justify-center' : 'px-3 py-2 text-xs'
                      } ${
                        isActive
                          ? 'bg-slate-800 text-cyan-400 border border-cyan-700/60 shadow-sm font-semibold'
                          : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
                      }`
                    }
                  >
                    <IconComponent
                      size={18}
                      className="shrink-0 transition-transform group-hover:scale-105"
                    />
                    {!isCollapsed && (
                      <span className="flex-1 truncate">{item.label}</span>
                    )}
                    {!isCollapsed && item.badge && (
                      <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer & Collapse Control */}
      <div className="p-3 border-t border-slate-800/90 bg-slate-950/60 space-y-2">
        {!isCollapsed && (
          <div className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400 font-mono space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Engine</span>
              <span className="text-cyan-400 font-medium">pgvector + RDKit</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Retrieval</span>
              <span className="text-emerald-400 font-medium">Hybrid RRF</span>
            </div>
          </div>
        )}

        {/* Collapse Button */}
        <button
          onClick={onToggleCollapse}
          type="button"
          aria-label={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors border border-slate-800/80"
        >
          {isCollapsed ? (
            <ChevronRightIcon size={16} />
          ) : (
            <>
              <ChevronLeftIcon size={16} />
              <span>Collapse Navigation</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
};
