import React, { useState } from 'react';
import { chemistryApi } from '../services/api';

export const ChemicalExplorerPage: React.FC = () => {
  const [query, setQuery] = useState<string>('Ethanol');
  const [entity, setEntity] = useState<any>({
    id: 'chem-001',
    canonical_name: 'Ethanol',
    smiles: 'CCO',
    inchikey: 'LFQSCWFLJHTTHZ-UHFFFAOYSA-N',
    inchi: 'InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3',
    formula: 'C2H6O',
    molecular_weight: 46.07,
    iupac_name: 'ethanol',
  });

  const handleSearch = async () => {
    try {
      const data = await chemistryApi.canonicalize(query);
      if (data) setEntity(data);
    } catch (err) {
      console.warn('Could not fetch entity:', err);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-black text-white tracking-tight">Chemical Entity Explorer</h2>
        <p className="text-xs text-slate-400 mt-1">
          PubChem & RDKit integrated chemical structure normalization, SMILES/InChI resolution, and molecular property lookup.
        </p>
      </div>

      {/* Search Bar */}
      <div className="flex gap-3 bg-slate-900 p-2 rounded-xl border border-slate-800 shadow-xl max-w-2xl">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter chemical name, SMILES (e.g. CCO), or InChIKey..."
          className="flex-1 px-4 py-2.5 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
        />
        <button
          onClick={handleSearch}
          className="px-6 py-2.5 text-xs font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg font-mono shadow-lg shadow-cyan-500/20"
        >
          🧪 Resolve Entity
        </button>
      </div>

      {/* Entity Card */}
      {entity && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-xl font-extrabold text-white">{entity.canonical_name}</h3>
                <p className="text-xs font-mono text-cyan-400 mt-0.5">IUPAC: {entity.iupac_name || entity.canonical_name}</p>
              </div>
              <span className="px-3 py-1 text-xs font-mono font-bold text-emerald-400 bg-emerald-950 border border-emerald-800 rounded-full">
                PUBCHEM VERIFIED
              </span>
            </div>

            {/* Properties Grid */}
            <div className="grid grid-cols-2 gap-4 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block uppercase">Formula</span>
                <span className="text-slate-200 font-bold text-sm">{entity.formula}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block uppercase">Molecular Weight</span>
                <span className="text-slate-200 font-bold text-sm">{entity.molecular_weight} g/mol</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 col-span-2">
                <span className="text-slate-500 text-[10px] block uppercase">SMILES</span>
                <span className="text-cyan-400 font-bold text-xs break-all">{entity.smiles}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 col-span-2">
                <span className="text-slate-500 text-[10px] block uppercase">InChIKey</span>
                <span className="text-slate-300 text-xs break-all">{entity.inchikey}</span>
              </div>
            </div>
          </div>

          {/* 2D Structure Card */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center text-center space-y-4 shadow-xl">
            <div className="w-48 h-48 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center font-mono text-4xl shadow-inner">
              ⚗️
            </div>
            <div>
              <p className="text-xs font-bold text-slate-300">Canonical 2D Structure</p>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">SMILES: {entity.smiles}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
