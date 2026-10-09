import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { healthApi } from '../../services/api';
import { HealthResponse } from '../../types';
import {
  ChatIcon,
  ChemicalIcon,
  DashboardIcon,
  DatabaseIcon,
  DocumentsIcon,
  EvaluationIcon,
  ExperimentsIcon,
  JobsIcon,
  MenuIcon,
  PlusIcon,
  SearchIcon,
  ServerIcon,
  SettingsIcon,
  ViewerIcon,
} from '../common/Icons';

interface NavbarProps {
  onToggleSidebar?: () => void;
  onMobileToggle?: () => void;
}

const routeTitles: Record<string, { label: string; icon: React.ComponentType<React.SVGProps<SVGSVGElement> & { size?: number }> }> = {
  '/': { label: 'Workspace Overview', icon: DashboardIcon },
  '/chat': { label: 'Research Chat', icon: ChatIcon },
  '/documents': { label: 'Document Library', icon: DocumentsIcon },
  '/viewer': { label: 'PDF & Citation Viewer', icon: ViewerIcon },
  '/search': { label: 'Hybrid Search', icon: SearchIcon },
  '/chemical': { label: 'Chemical Entity Explorer', icon: ChemicalIcon },
  '/experiments': { label: 'Experimental Records', icon: ExperimentsIcon },
  '/jobs': { label: 'Processing Pipeline', icon: JobsIcon },
  '/evaluation': { label: 'Retrieval Metrics', icon: EvaluationIcon },
  '/settings': { label: 'Settings & Diagnostics', icon: SettingsIcon },
};

export const Navbar: React.FC<NavbarProps> = ({ onMobileToggle }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await healthApi.getHealth();
        setHealth(data);
      } catch (err) {
        console.warn('Could not fetch system health:', err);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const isHealthy = health?.status === 'ok';
  const dbStatus = health?.services?.find((s) => s.name === 'database')?.status === 'ok';
  const redisStatus = health?.services?.find((s) => s.name === 'redis')?.status === 'ok';

  const currentRouteInfo = routeTitles[location.pathname] || {
    label: 'ChemRAG Workspace',
    icon: DashboardIcon,
  };
  const RouteIcon = currentRouteInfo.icon;

  return (
    <header className="h-14 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 px-4 md:px-6 flex items-center justify-between sticky top-0 z-30 shrink-0 text-slate-100">
      {/* Left Section: Mobile Menu + Breadcrumb & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMobileToggle}
          type="button"
          aria-label="Toggle Navigation Menu"
          className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <MenuIcon size={20} />
        </button>

        <div className="flex items-center gap-2 text-slate-400 text-xs font-mono">
          <span className="hidden sm:inline font-semibold text-slate-400">ChemRAG</span>
          <span className="hidden sm:inline text-slate-600">/</span>
          <div className="flex items-center gap-2 text-slate-100 font-sans font-semibold text-sm">
            <RouteIcon size={16} className="text-cyan-400" />
            <span>{currentRouteInfo.label}</span>
          </div>
        </div>
      </div>

      {/* Right Section: System Health Badges + Quick Action */}
      <div className="flex items-center gap-3">
        {/* Real-Time System Health Badges */}
        <div className="hidden lg:flex items-center gap-2 text-xs font-mono">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 text-slate-300">
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span className="font-medium">System: {isHealthy ? 'ONLINE' : 'DEGRADED'}</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 text-slate-300">
            <DatabaseIcon size={13} className="text-slate-400" />
            <span>DB:</span>
            <span className={dbStatus ? 'text-emerald-400 font-semibold' : 'text-amber-400'}>
              {dbStatus ? 'PGVECTOR' : 'OFFLINE'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 text-slate-300">
            <ServerIcon size={13} className="text-slate-400" />
            <span>Cache:</span>
            <span className={redisStatus ? 'text-cyan-400 font-semibold' : 'text-amber-400'}>
              {redisStatus ? 'REDIS' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {/* Action Shortcut */}
        <button
          onClick={() => navigate('/chat')}
          type="button"
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold shadow-md transition-all border border-cyan-400/30"
        >
          <PlusIcon size={15} />
          <span className="hidden sm:inline">New Research Query</span>
        </button>
      </div>
    </header>
  );
};
