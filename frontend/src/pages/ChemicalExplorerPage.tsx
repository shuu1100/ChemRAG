import React, { useState, useEffect } from 'react';
import { chemistryApi } from '../services/api';
import { ChemicalEntity } from '../types';

export const ChemicalExplorerPage: React.FC = () => {
  const [query, setQuery] = useState<string>('Oxygen');
  const [entity, setEntity] = useState<ChemicalEntity | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery !== undefined ? searchQuery : query;
    if (!q || !q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await chemistryApi.canonicalize(q.trim());
      setEntity(data);
    } catch (err: any) {
      console.warn('Could not fetch entity:', err);
      setEntity(null);
      setError(err?.message || `Could not resolve chemical structure for '${q}'`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleSearch('Oxygen');
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-black text-white tracking-tight">Chemical Entity Explorer</h2>
        <p className="text-xs text-slate-400 mt-1">
          PubChem & RDKit integrated chemical structure normalization, SMILES/InChI resolution, and 2D molecular structure rendering.
        </p>
      </div>

      {/* Search Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
        className="flex gap-3 bg-slate-900 p-2 rounded-xl border border-slate-800 shadow-xl max-w-2xl"
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter chemical name (e.g. Oxygen, Ethanol), SMILES (e.g. O=O, CCO), or InChIKey..."
          className="flex-1 px-4 py-2.5 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2.5 text-xs font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 rounded-lg font-mono shadow-lg shadow-cyan-500/20 flex items-center gap-2"
        >
          {loading ? (
            <span className="inline-block animate-spin rounded-full h-3 w-3 border-2 border-slate-950 border-t-transparent" />
          ) : (
            '🧪'
          )}
          Resolve Entity
        </button>
      </form>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800/80 text-red-200 text-xs font-mono max-w-2xl shadow-lg flex items-start gap-3">
          <span className="text-lg">⚠️</span>
          <div>
            <p className="font-bold">Structure Resolution Error</p>
            <p className="mt-1 text-red-300">{error}</p>
          </div>
        </div>
      )}

      {/* Quick Search Chips */}
      <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
        <span>Try sample queries:</span>
        {['Oxygen', 'Ethanol', 'Aspirin', 'Caffeine', 'O=O'].map((sample) => (
          <button
            key={sample}
            onClick={() => {
              setQuery(sample);
              handleSearch(sample);
            }}
            className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 text-[11px]"
          >
            {sample}
          </button>
        ))}
      </div>

      {/* Entity Card */}
      {entity && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-xl font-extrabold text-white">{entity.canonical_name || entity.iupac_name}</h3>
                <p className="text-xs font-mono text-cyan-400 mt-0.5">IUPAC: {entity.iupac_name || entity.canonical_name}</p>
              </div>
              <span className="px-3 py-1 text-xs font-mono font-bold text-emerald-400 bg-emerald-950 border border-emerald-800 rounded-full uppercase">
                {entity.data_source || (entity.cid ? 'PUBCHEM VERIFIED' : 'RDKIT VERIFIED')}
              </span>
            </div>

            {/* Properties Grid */}
            <div className="grid grid-cols-2 gap-4 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block uppercase">Formula</span>
                <span className="text-slate-200 font-bold text-sm">{entity.formula || 'N/A'}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block uppercase">Molecular Weight</span>
                <span className="text-slate-200 font-bold text-sm">
                  {entity.molecular_weight ? `${entity.molecular_weight} g/mol` : 'N/A'}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 col-span-2">
                <span className="text-slate-500 text-[10px] block uppercase">SMILES</span>
                <span className="text-cyan-400 font-bold text-xs break-all">{entity.smiles || 'N/A'}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 col-span-2">
                <span className="text-slate-500 text-[10px] block uppercase">InChIKey</span>
                <span className="text-slate-300 text-xs break-all">{entity.inchikey || 'N/A'}</span>
              </div>
              {entity.inchi && (
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 col-span-2">
                  <span className="text-slate-500 text-[10px] block uppercase">InChI</span>
                  <span className="text-slate-400 text-[11px] break-all">{entity.inchi}</span>
                </div>
              )}
            </div>
          </div>

          {/* 2D Structure Card */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center text-center space-y-4 shadow-xl">
            <div className="w-56 h-56 rounded-xl bg-slate-950 border border-slate-800 p-2 flex items-center justify-center overflow-hidden shadow-inner">
              {entity.structure_svg ? (
                <div
                  className="w-full h-full flex items-center justify-center [&>svg]:max-w-full [&>svg]:max-h-full [&>svg]:w-full [&>svg]:h-full"
                  dangerouslySetInnerHTML={{ __html: entity.structure_svg }}
                />
              ) : entity.structure_url ? (
                <img
                  src={entity.structure_url}
                  alt={`2D molecular structure of ${entity.canonical_name}`}
                  className="max-w-full max-h-full object-contain filter invert opacity-90"
                />
              ) : (
                <div className="text-slate-500 text-xs font-mono p-4">
                  <p className="text-lg mb-1">🚫</p>
                  <p className="font-bold">Structure unavailable</p>
                  <p className="text-[10px] text-slate-600 mt-1">No 2D diagram generated for SMILES: {entity.smiles || 'none'}</p>
                </div>
              )}
            </div>
            <div>
              <p className="text-xs font-bold text-slate-300">Canonical 2D Structure</p>
              <p className="text-[11px] text-cyan-400 font-mono mt-0.5 break-all">
                SMILES: {entity.smiles || 'Unavailable'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
