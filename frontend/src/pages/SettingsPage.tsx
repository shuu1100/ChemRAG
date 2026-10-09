import React, { useState } from 'react';

export const SettingsPage: React.FC = () => {
  const [efSearch, setEfSearch] = useState<number>(100);
  const [llmModel, setLlmModel] = useState<string>('gpt-4o');

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h2 className="text-2xl font-black text-white tracking-tight">System Settings & Configuration</h2>
        <p className="text-xs text-slate-400 mt-1">
          Configure LLM providers, vector search HNSW parameters, safety guardrails, and environment policies.
        </p>
      </div>

      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6 shadow-xl">
        <h3 className="text-sm font-extrabold text-slate-200 uppercase tracking-wider border-b border-slate-800 pb-3">
          LLM & Embedding Provider
        </h3>

        <div className="space-y-4 font-mono text-xs">
          <div>
            <label className="block text-slate-400 mb-1">Primary LLM Model</label>
            <select
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200"
            >
              <option value="gpt-4o">OpenAI gpt-4o (Default)</option>
              <option value="claude-3-5-sonnet">Anthropic Claude 3.5 Sonnet</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">HNSW Query Search Depth (hnsw.ef_search)</label>
            <input
              type="number"
              value={efSearch}
              onChange={(e) => setEfSearch(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-200"
            />
            <p className="text-[10px] text-slate-500 mt-1">Higher values increase retrieval recall accuracy for dense 3072d vectors.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
