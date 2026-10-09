import React, { useEffect, useState } from 'react';
import { healthApi } from '../../services/api';
import { HealthResponse } from '../../types';

export const Navbar: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await healthApi.getHealth();
        setHealth(data);
      } catch (err) {
        console.warn('Could not fetch health:', err);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const isHealthy = health?.status === 'ok';

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-700 flex items-center justify-center font-mono font-bold text-white shadow-lg shadow-cyan-500/20">
          ⚗️
        </div>
        <div>
          <h1 className="text-lg font-extrabold tracking-tight text-white flex items-center gap-2">
            ChemRAG <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">v0.1.0</span>
          </h1>
          <p className="text-[11px] text-slate-400">Scientific Intelligence & Chemical RAG Platform</p>
        </div>
      </div>

      {/* System Health Indicators */}
      <div className="flex items-center gap-4 text-xs font-mono">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700">
          <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className="text-slate-300">System: {isHealthy ? 'ONLINE' : 'DEGRADED'}</span>
        </div>

        {health && (
          <div className="hidden md:flex items-center gap-3 text-slate-400 border-l border-slate-800 pl-4">
            <span title="PostgreSQL + pgvector">
              DB:{' '}
              <strong className={health.services.find((s) => s.name === 'database')?.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}>
                {health.services.find((s) => s.name === 'database')?.status === 'ok' ? 'PGVECTOR' : 'OFFLINE'}
              </strong>
            </span>
            <span title="Redis Cache">
              Cache:{' '}
              <strong className={health.services.find((s) => s.name === 'redis')?.status === 'ok' ? 'text-cyan-400' : 'text-amber-400'}>
                {health.services.find((s) => s.name === 'redis')?.status === 'ok' ? 'REDIS' : 'OFFLINE'}
              </strong>
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
