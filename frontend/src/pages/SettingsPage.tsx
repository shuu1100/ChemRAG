import React, { useState } from 'react';

export const SettingsPage: React.FC = () => {
  const [efSearch, setEfSearch] = useState<number>(100);
  const [llmModel, setLlmModel] = useState<string>('gpt-4o');

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">System Settings & Configuration</h2>
        <p className="text-xs text-slate-400 mt-1">
          Configure LLM providers, vector search HNSW parameters, safety guardrails, and environment policies.
        </p>
      </div>

      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-6 shadow-md">
        <h3 className="text-xs font-bold text-slate-300 uppercase font-mono tracking-wider border-b border-slate-800 pb-3">
          LLM & Embedding Provider Parameters
        </h3>

        <div className="space-y-4 font-mono text-xs">
          <div>
            <label className="block text-slate-400 mb-1 font-sans font-semibold">Primary LLM Model</label>
            <select
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="gpt-4o">OpenAI gpt-4o (Default)</option>
              <option value="claude-3-5-sonnet">Anthropic Claude 3.5 Sonnet</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1 font-sans font-semibold">HNSW Query Search Depth (hnsw.ef_search)</label>
            <input
              type="number"
              value={efSearch}
              onChange={(e) => setEfSearch(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500"
            />
            <p className="text-[11px] text-slate-500 mt-1 font-sans">Higher values increase retrieval recall accuracy for dense 3072d vectors.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
