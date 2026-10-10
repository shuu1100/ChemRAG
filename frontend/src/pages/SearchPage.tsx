import React, { useState } from 'react';
import { CitationBadge } from '../components/citations/CitationBadge';
import { searchApi } from '../services/api';

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState<string>('Ethanol boiling point and thermodynamic properties');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [results, setResults] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanQuery = query.trim();
    if (!cleanQuery || isSearching) return;

    setIsSearching(true);
    setErrorMsg(null);
    setHasSearched(true);

    try {
      const data = await searchApi.searchHybrid(cleanQuery, 10);
      setResults(data.results || []);
    } catch (err: any) {
      console.warn('Search failed:', err);
      setResults([]);
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Hybrid search service encountered an error.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-black text-slate-900 tracking-tight">Hybrid Literature Search</h2>
        <p className="text-xs text-slate-500 mt-1">
          Combines PostgreSQL ts_rank_cd Cover Density lexical search with pgvector 3072d HNSW semantic similarity & Cross-Encoder reranking.
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="flex gap-3 bg-white p-2 rounded-xl border border-slate-200 shadow-sm max-w-4xl">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask or search scientific query (e.g. Ethanol rate constant, CAS 64-17-5, synthesis yield)..."
          className="flex-1 px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-cyan-500 focus:bg-white font-sans"
        />
        <button
          type="submit"
          disabled={isSearching || !query.trim()}
          className="px-6 py-2.5 text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 rounded-lg shadow-sm font-mono flex items-center gap-2"
        >
          {isSearching ? (
            <>
              <span className="inline-block animate-spin rounded-full h-3 w-3 border-2 border-white border-t-transparent" />
              Searching...
            </>
          ) : (
            '🔍 Search Corpus'
          )}
        </button>
      </form>

      {/* Sample Quick Query Chips */}
      <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
        <span>Try sample searches:</span>
        {['Ethanol boiling point', 'Pt/Al2O3 catalyst', 'Binary Mixtures', 'O=O oxygen'].map((sample) => (
          <button
            key={sample}
            onClick={() => {
              setQuery(sample);
              setTimeout(() => handleSearch(), 50);
            }}
            className="px-2.5 py-1 rounded-md bg-white hover:bg-slate-100 text-cyan-700 border border-slate-200 font-bold text-[11px] shadow-2xs"
          >
            {sample}
          </button>
        ))}
      </div>

      {/* Error Callout State */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono max-w-4xl shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠️</span>
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => handleSearch()} className="px-3 py-1 bg-rose-600 text-white font-bold rounded-md hover:bg-rose-700">
            Retry Search
          </button>
        </div>
      )}

      {/* Loading Skeleton State */}
      {isSearching && (
        <div className="p-12 text-center text-slate-400 font-mono space-y-2 bg-white rounded-xl border border-slate-200 shadow-sm max-w-4xl">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-3 border-cyan-600 border-t-transparent mb-2" />
          <p className="font-bold text-slate-700 text-sm">Executing Multi-Modal Hybrid Retrieval...</p>
          <p className="text-xs text-slate-500">Querying pgvector HNSW index & PostgreSQL full-text search engine</p>
        </div>
      )}

      {/* Empty State: Has searched but 0 results */}
      {!isSearching && hasSearched && !errorMsg && results.length === 0 && (
        <div className="p-12 text-center text-slate-400 font-mono space-y-2 bg-white rounded-xl border border-slate-200 shadow-sm max-w-4xl">
          <p className="text-2xl">🔍</p>
          <p className="font-bold text-slate-800 text-sm">No Matching Passages Found in Indexed Corpus</p>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            No scientific document chunks matched your query '{query}'. Upload additional PDFs in the Document Library or try broadening your search terms.
          </p>
        </div>
      )}

      {/* Results List State */}
      {!isSearching && results.length > 0 && (
        <div className="space-y-4 max-w-4xl">
          <div className="flex items-center justify-between text-xs font-mono text-slate-500 px-1">
            <span>Found {results.length} relevant scientific passage{results.length === 1 ? '' : 's'}</span>
            <span className="text-emerald-700 font-bold">● Ranked via Reciprocal Rank Fusion & Cross-Encoder</span>
          </div>

          {results.map((res, idx) => {
            const docTitle = res.document_title || res.metadata?.document_title || 'Scientific Literature Paper';
            const pageNum = res.page_number || 1;
            const scorePct = (res.score * 100).toFixed(1);
            const breakdown = res.score_breakdown || {};

            return (
              <div key={res.chunk_id || idx} className="p-5 rounded-xl bg-white border border-slate-200 space-y-3 shadow-sm hover:border-cyan-300 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CitationBadge citationId={`CIT-00${idx + 1}`} documentTitle={docTitle} pageNumber={pageNum} />
                    <span className="text-sm font-extrabold text-slate-900">{docTitle}</span>
                    <span className="text-[11px] font-mono text-slate-500 font-bold bg-slate-100 px-2 py-0.5 rounded">
                      Page {pageNum}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 text-xs font-mono font-bold text-cyan-700 bg-cyan-50 border border-cyan-200 rounded-full">
                      Score: {scorePct}%
                    </span>
                    {res.document_id && (
                      <a
                        href={`/api/v1/documents/${res.document_id}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 text-[11px] font-mono font-bold text-cyan-700 hover:text-cyan-800 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded"
                      >
                        📄 Open PDF
                      </a>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-800 font-sans leading-relaxed bg-slate-50 p-3.5 rounded-lg border border-slate-200">
                  {res.content}
                </p>

                {breakdown && (
                  <div className="flex gap-4 font-mono text-[10px] text-slate-500 pt-1 flex-wrap">
                    {breakdown.semantic_score !== undefined && (
                      <span>Semantic: <strong className="text-slate-700">{(breakdown.semantic_score * 100).toFixed(0)}%</strong></span>
                    )}
                    {breakdown.lexical_score !== undefined && (
                      <span>Lexical (ts_rank_cd): <strong className="text-slate-700">{(breakdown.lexical_score * 100).toFixed(0)}%</strong></span>
                    )}
                    {breakdown.reranker_score !== undefined && (
                      <span>Reranker (Cross-Encoder): <strong className="text-cyan-700">{(breakdown.reranker_score * 100).toFixed(0)}%</strong></span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default SearchPage;
