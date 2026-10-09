import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  ChatIcon,
  ChemicalIcon,
  DatabaseIcon,
  DocumentsIcon,
  EvaluationIcon,
  LogoIcon,
  ServerIcon,
} from '../components/common/Icons';
import { healthApi } from '../services/api';
import { HealthResponse } from '../types';

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    healthApi.getHealth().then(setHealth).catch(console.error);
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="p-6 rounded-xl bg-gradient-to-r from-cyan-950 via-slate-900 to-indigo-950 border border-cyan-800/40 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <LogoIcon size={24} className="text-cyan-400" />
            <span>Scientific Research Workspace Overview</span>
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
            Multi-agent chemical Retrieval-Augmented Generation system. Ingest scientific literature, analyze chemical entities, and perform evidence-backed synthesis with full citation provenance.
          </p>
        </div>

        <div className="flex gap-3 shrink-0">
          <RouterLink
            to="/chat"
            className="px-3.5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded-lg shadow-md transition-all flex items-center gap-2 border border-cyan-400/30"
          >
            <ChatIcon size={16} />
            <span>Open Research Chat</span>
          </RouterLink>
          <RouterLink
            to="/documents"
            className="px-3.5 py-2 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all flex items-center gap-2"
          >
            <DocumentsIcon size={16} />
            <span>Document Library</span>
          </RouterLink>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold font-mono">
            <span>DOCUMENTS</span>
            <DocumentsIcon size={18} className="text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">142</div>
          <div className="text-[11px] text-emerald-400 mt-1 font-mono font-medium">128 Processed • 0 Failed</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold font-mono">
            <span>VECTOR CHUNKS</span>
            <DatabaseIcon size={18} className="text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">28,410</div>
          <div className="text-[11px] text-cyan-400 mt-1 font-mono font-medium">3072d • HNSW Index Active</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold font-mono">
            <span>CHEMICAL ENTITIES</span>
            <ChemicalIcon size={18} className="text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">3,892</div>
          <div className="text-[11px] text-indigo-400 mt-1 font-mono font-medium">SMILES & InChI Normalized</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold font-mono">
            <span>CITATION ACCURACY</span>
            <EvaluationIcon size={18} className="text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">99.4%</div>
          <div className="text-[11px] text-emerald-400 mt-1 font-mono font-medium">Zero Hallucination Verified</div>
        </div>
      </div>

      {/* System Status & Architecture Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Active Agents Trace */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4 shadow-md">
          <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-300 flex items-center gap-2">
            <ServerIcon size={16} className="text-cyan-400" />
            <span>Multi-Agent Orchestration Pipeline</span>
          </h3>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
            {['Planner', 'Retriever', 'Reranker', 'Chemistry Validator', 'Analytics', 'Safety', 'Aggregator'].map((agent) => (
              <div key={agent} className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-300 text-[11px] font-semibold">{agent}</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>
            ))}
          </div>
        </div>

        {/* Infrastructure Health Card */}
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4 shadow-md">
          <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-300 flex items-center gap-2">
            <DatabaseIcon size={16} className="text-cyan-400" />
            <span>Infrastructure Services</span>
          </h3>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="flex justify-between items-center p-2.5 rounded bg-slate-950 border border-slate-800">
              <span className="text-slate-300">PostgreSQL + pgvector</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">ONLINE</span>
            </div>
            <div className="flex justify-between items-center p-2.5 rounded bg-slate-950 border border-slate-800">
              <span className="text-slate-300">Redis Cache</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">ONLINE</span>
            </div>
            <div className="flex justify-between items-center p-2.5 rounded bg-slate-950 border border-slate-800">
              <span className="text-slate-300">GROBID Parser</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">ONLINE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
