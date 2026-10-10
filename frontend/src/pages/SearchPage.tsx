import React, { useState } from 'react';
import { CitationBadge } from '../components/citations/CitationBadge';
import { searchApi } from '../services/api';

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState<string>('Ethanol boiling point and thermodynamic properties');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [results, setResults] = useState<any[]>([]);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    setErrorMsg(null);
    try {
      const data = await searchApi.searchHybrid(query, 5);
      setResults(data.results || []);
    } catch (err: any) {
      console.warn('Search failed:', err);
      setResults([]);
      setErrorMsg(err?.response?.data?.detail || 'Hybrid search endpoint returned no matches or error.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-black text-slate-900 tracking-tight">Hybrid Literature Search</h2>
        <p className="text-xs text-slate-500 mt-1">
          Combines PostgreSQL ts_rank_cd Cover Density lexical search with pgvector 3072d HNSW semantic similarity & Cohere Rerank.
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="flex gap-3 bg-white p-2 rounded-xl border border-slate-200 shadow-sm">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Ask or search scientific query (e.g. Ethanol rate constant, CAS 64-17-5, synthesis yield)..."
          className="flex-1 px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-cyan-500 focus:bg-white font-sans"
        />
        <button
          onClick={handleSearch}
          disabled={isSearching}
          className="px-6 py-2.5 text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 rounded-lg shadow-sm font-mono"
        >
          {isSearching ? 'Searching...' : '🔍 Search'}
        </button>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        {results.map((res, idx) => (
          <div key={res.chunk_id || idx} className="p-5 rounded-xl bg-white border border-slate-200 space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CitationBadge citationId={`CIT-00${idx + 1}`} documentTitle={res.document_title} pageNumber={res.page_number} />
                <span className="text-xs font-bold text-slate-900">{res.document_title}</span>
                <span className="text-[10px] font-mono text-slate-500">Page {res.page_number}</span>
              </div>
              <span className="px-2 py-0.5 text-[11px] font-mono font-bold text-cyan-700 bg-cyan-50 border border-cyan-200 rounded">
                Score: {(res.score * 100).toFixed(1)}%
              </span>
            </div>

            <p className="text-xs text-slate-800 font-sans leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200">
              {res.content}
            </p>

            {res.score_breakdown && (
              <div className="flex gap-4 font-mono text-[10px] text-slate-500 pt-1">
                <span>Semantic: <strong className="text-slate-700">{(res.score_breakdown.semantic_score * 100).toFixed(0)}%</strong></span>
                <span>Lexical (ts_rank_cd): <strong className="text-slate-700">{(res.score_breakdown.lexical_score * 100).toFixed(0)}%</strong></span>
                <span>Reranker (Cohere): <strong className="text-cyan-700">{(res.score_breakdown.rerank_score * 100).toFixed(0)}%</strong></span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
