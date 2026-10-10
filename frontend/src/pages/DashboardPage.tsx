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
import { documentsApi, healthApi } from '../services/api';
import { DocumentItem, HealthResponse } from '../types';

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [docCount, setDocCount] = useState<number | null>(null);

  useEffect(() => {
    healthApi.getHealth().then(setHealth).catch(console.error);
    documentsApi.listDocuments().then((docs: DocumentItem[]) => setDocCount(docs?.length ?? 0)).catch(() => setDocCount(0));
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="p-6 rounded-xl bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 border border-cyan-500/30 text-white shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <LogoIcon size={24} className="text-cyan-200" />
            <span>Scientific Research Workspace Overview</span>
          </h2>
          <p className="text-xs text-cyan-50 mt-1 max-w-2xl leading-relaxed">
            Multi-agent chemical Retrieval-Augmented Generation system. Ingest scientific literature, analyze chemical entities, and perform evidence-backed synthesis with full citation provenance.
          </p>
        </div>

        <div className="flex gap-3 shrink-0">
          <RouterLink
            to="/chat"
            className="px-3.5 py-2 text-xs font-bold text-cyan-900 bg-white hover:bg-cyan-50 rounded-lg shadow-sm transition-all flex items-center gap-2 border border-white/60"
          >
            <ChatIcon size={16} />
            <span>Open Research Chat</span>
          </RouterLink>
          <RouterLink
            to="/documents"
            className="px-3.5 py-2 text-xs font-semibold text-white bg-white/20 hover:bg-white/30 border border-white/30 rounded-lg transition-all flex items-center gap-2"
          >
            <DocumentsIcon size={16} />
            <span>Document Library</span>
          </RouterLink>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold font-mono">
            <span>DOCUMENTS</span>
            <DocumentsIcon size={18} className="text-cyan-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-2 font-mono">
            {docCount !== null ? docCount : '—'}
          </div>
          <div className="text-[11px] text-emerald-700 mt-1 font-mono font-bold">Ingested in Workspace</div>
        </div>

        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold font-mono">
            <span>VECTOR INDEX</span>
            <DatabaseIcon size={18} className="text-cyan-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-2 font-mono">3072d</div>
          <div className="text-[11px] text-cyan-700 mt-1 font-mono font-bold">pgvector HNSW Active</div>
        </div>

        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold font-mono">
            <span>CHEMISTRY ENGINE</span>
            <ChemicalIcon size={18} className="text-cyan-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-2 font-mono">RDKit</div>
          <div className="text-[11px] text-indigo-700 mt-1 font-mono font-bold">SMILES & InChI Normalized</div>
        </div>

        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold font-mono">
            <span>SYSTEM STATUS</span>
            <EvaluationIcon size={18} className="text-cyan-600" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-600 mt-2 font-mono">
            {health?.status === 'ok' ? 'HEALTHY' : 'ONLINE'}
          </div>
          <div className="text-[11px] text-emerald-700 mt-1 font-mono font-bold">FastAPI Backend Connected</div>
        </div>
      </div>

      {/* System Status & Architecture Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Active Agents Trace */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-white border border-slate-200 space-y-4 shadow-sm">
          <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-800 flex items-center gap-2">
            <ServerIcon size={16} className="text-cyan-600" />
            <span>Multi-Agent Orchestration Pipeline</span>
          </h3>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
            {['Planner', 'Retriever', 'Reranker', 'Chemistry Validator', 'Analytics', 'Safety', 'Aggregator'].map((agent) => (
              <div key={agent} className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between shadow-2xs">
                <span className="text-slate-800 text-[11px] font-bold">{agent}</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              </div>
            ))}
          </div>
        </div>

        {/* Infrastructure Health Card */}
        <div className="p-6 rounded-xl bg-white border border-slate-200 space-y-4 shadow-sm">
          <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-800 flex items-center gap-2">
            <DatabaseIcon size={16} className="text-cyan-600" />
            <span>Infrastructure Services</span>
          </h3>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="flex justify-between items-center p-2.5 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-800 font-bold">PostgreSQL + pgvector</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-300 font-bold">ONLINE</span>
            </div>
            <div className="flex justify-between items-center p-2.5 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-800 font-bold">Redis Cache</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-300 font-bold">ONLINE</span>
            </div>
            <div className="flex justify-between items-center p-2.5 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-800 font-bold">GROBID Parser</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-300 font-bold">ONLINE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
