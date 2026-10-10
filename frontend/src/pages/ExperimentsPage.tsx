import React, { useEffect, useState } from 'react';
import { ExperimentsIcon, SearchIcon } from '../components/common/Icons';
import { experimentsApi } from '../services/api';

interface ExperimentItem {
  id: string;
  document_id: string;
  document_title?: string;
  description?: string;
  experimental_conditions?: {
    temperature_celsius?: number;
    pressure_bar?: number;
    solvent?: string;
    catalyst?: string;
    reaction_time_hours?: number;
  };
  results?: {
    yield_percentage?: number;
  };
  chemical_participants?: Array<{ role: string; name: string }>;
  confidence?: number;
  created_at?: string;
}

export const ExperimentsPage: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filters
  const [chemicalFilter, setChemicalFilter] = useState<string>('');
  const [solventFilter, setSolventFilter] = useState<string>('');
  const [catalystFilter, setCatalystFilter] = useState<string>('');
  const [selectedExp, setSelectedExp] = useState<ExperimentItem | null>(null);

  const fetchExperiments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await experimentsApi.listExperiments({
        chemical: chemicalFilter.trim() || undefined,
        solvent: solventFilter.trim() || undefined,
        catalyst: catalystFilter.trim() || undefined,
      });
      setExperiments(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.warn('Experiments API error:', err);
      setError(err?.message || 'Failed to fetch experimental records');
      setExperiments([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchExperiments();
  }, [chemicalFilter, solventFilter, catalystFilter]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ExperimentsIcon size={22} className="text-cyan-600" />
            <span>Experimental Records & Reaction Extraction</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Structured experimental parameter extraction from ingested papers: reaction procedures, temperature/pressure conditions, solvents, catalysts, and yields.
          </p>
        </div>
        <button
          onClick={fetchExperiments}
          className="px-3.5 py-1.5 text-xs font-mono font-bold text-cyan-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs self-start sm:self-auto"
        >
          🔄 Refresh Records
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono">
          ⚠️ {error}
        </div>
      )}

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm font-mono text-xs">
        <div className="relative">
          <input
            type="text"
            placeholder="Filter by chemical substance (e.g. Ethanol)..."
            value={chemicalFilter}
            onChange={(e) => setChemicalFilter(e.target.value)}
            className="w-full pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-cyan-500"
          />
          <SearchIcon size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
        </div>
        <div>
          <input
            type="text"
            placeholder="Filter by solvent (e.g. Water, THF)..."
            value={solventFilter}
            onChange={(e) => setSolventFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-cyan-500"
          />
        </div>
        <div>
          <input
            type="text"
            placeholder="Filter by catalyst (e.g. Pt/Al2O3)..."
            value={catalystFilter}
            onChange={(e) => setCatalystFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* Experiments Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500">
              <th className="p-4">Source Document</th>
              <th className="p-4">Procedure Description</th>
              <th className="p-4">Conditions</th>
              <th className="p-4">Reported Yield</th>
              <th className="p-4">Confidence</th>
              <th className="p-4 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs font-sans">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="p-12 text-center text-slate-400 font-mono">
                  <div className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-cyan-600 border-t-transparent mb-2" />
                  <p>Loading experimental records from PostgreSQL...</p>
                </td>
              </tr>
            ) : experiments.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-12 text-center text-slate-400 font-mono">
                  <p className="text-base font-bold text-slate-700 mb-1">No Extracted Experimental Records</p>
                  <p className="text-xs">Upload scientific papers containing experimental synthesis sections to populate structured records.</p>
                </td>
              </tr>
            ) : (
              experiments.map((exp) => {
                const conds = exp.experimental_conditions || {};
                const yieldPct = exp.results?.yield_percentage;

                return (
                  <tr key={exp.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 font-semibold text-slate-800 max-w-xs truncate">
                      {exp.document_title || 'Scientific Paper'}
                    </td>
                    <td className="p-4 text-slate-700 max-w-md truncate">
                      {exp.description || 'No description extracted'}
                    </td>
                    <td className="p-4 font-mono text-[11px] text-slate-600">
                      {conds.temperature_celsius !== undefined && <div>Temp: {conds.temperature_celsius}°C</div>}
                      {conds.solvent && <div className="text-cyan-700 font-bold">Solvent: {conds.solvent}</div>}
                      {conds.catalyst && <div>Catalyst: {conds.catalyst}</div>}
                      {!conds.temperature_celsius && !conds.solvent && !conds.catalyst && <span className="text-slate-400">Ambient</span>}
                    </td>
                    <td className="p-4 font-mono font-bold text-emerald-700">
                      {yieldPct !== undefined ? `${yieldPct}%` : 'N/A'}
                    </td>
                    <td className="p-4 font-mono text-[11px]">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold">
                        {Math.round((exp.confidence || 0.85) * 100)}%
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => setSelectedExp(exp)}
                        className="px-2.5 py-1 text-xs font-mono font-bold text-cyan-700 bg-cyan-50 border border-cyan-200 rounded hover:bg-cyan-100"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Record Modal */}
      {selectedExp && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-lg font-bold text-slate-900">Experimental Record Detail</h3>
              <button
                onClick={() => setSelectedExp(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 font-mono font-bold block uppercase text-[10px]">Source Paper</span>
                <p className="font-semibold text-slate-800">{selectedExp.document_title || 'Scientific Paper'}</p>
              </div>
              <div>
                <span className="text-slate-400 font-mono font-bold block uppercase text-[10px]">Procedure Extract</span>
                <p className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-700 font-sans leading-relaxed">
                  {selectedExp.description}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 font-mono">
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase font-bold">Temperature</span>
                  <span className="font-bold text-slate-800">
                    {selectedExp.experimental_conditions?.temperature_celsius !== undefined
                      ? `${selectedExp.experimental_conditions.temperature_celsius} °C`
                      : 'Not reported'}
                  </span>
                </div>
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase font-bold">Solvent</span>
                  <span className="font-bold text-cyan-700">
                    {selectedExp.experimental_conditions?.solvent || 'Not reported'}
                  </span>
                </div>
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase font-bold">Catalyst</span>
                  <span className="font-bold text-slate-800">
                    {selectedExp.experimental_conditions?.catalyst || 'None'}
                  </span>
                </div>
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase font-bold">Reported Yield</span>
                  <span className="font-bold text-emerald-700">
                    {selectedExp.results?.yield_percentage !== undefined
                      ? `${selectedExp.results.yield_percentage} %`
                      : 'Not reported'}
                  </span>
                </div>
              </div>
            </div>
            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedExp(null)}
                className="px-4 py-2 bg-cyan-600 text-white font-bold rounded-lg text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExperimentsPage;
