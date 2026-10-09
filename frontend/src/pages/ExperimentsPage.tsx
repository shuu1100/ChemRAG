import React from 'react';
import { ExperimentsIcon } from '../components/common/Icons';

export const ExperimentsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <ExperimentsIcon size={22} className="text-cyan-400" />
          <span>Experimental Records & Reaction Extraction</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Structured experimental parameter extraction from scientific papers, tables, and reaction schemas.
        </p>
      </div>

      <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 shadow-xl text-center max-w-2xl mx-auto">
        <div className="w-12 h-12 rounded-xl bg-cyan-950 text-cyan-400 border border-cyan-800/80 flex items-center justify-center mx-auto shadow-inner">
          <ExperimentsIcon size={24} />
        </div>
        <div className="space-y-2">
          <h3 className="text-base font-bold text-slate-200">Module Under Development (Planned Stage)</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Automatic chemical reaction extraction, reaction yield parsing, temperature/catalyst/solvent condition mapping, and experiment indexing will be implemented in upcoming pipeline stages.
          </p>
        </div>
        <div className="pt-2">
          <span className="inline-block px-3 py-1 text-[11px] font-mono text-cyan-400 bg-slate-950 border border-slate-800 rounded-full font-semibold">
            Status: Feature Placeholder — Not Yet Integrated with Backend
          </span>
        </div>
      </div>
    </div>
  );
};

export default ExperimentsPage;
