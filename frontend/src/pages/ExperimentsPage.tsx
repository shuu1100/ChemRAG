import React from 'react';

const mockExperiments = [
  {
    id: 'exp-001',
    reaction_name: 'Catalytic Hydrogenation of Bio-Ethanol',
    yield_pct: 94.2,
    temp: '350 °C',
    catalyst: 'Pt/Al2O3',
    solvent: 'Water',
    paper: 'Thermodynamics of Ethanol-Water Mixtures',
    citation_id: 'CIT-001',
  },
  {
    id: 'exp-002',
    reaction_name: 'Vapor-Liquid Phase Equilibrium Measurement',
    yield_pct: 98.6,
    temp: '78.37 °C',
    catalyst: 'N/A',
    solvent: 'Ethanol-Water Binary',
    paper: 'Binary Phase Equilibria and Critical Constants',
    citation_id: 'CIT-002',
  },
];

export const ExperimentsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Experimental Data & Reaction Extraction</h2>
        <p className="text-xs text-slate-400 mt-1">
          Structured experimental parameter extraction from scholarly PDF tables, text, and chemical reaction schema.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-md">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-950 border-b border-slate-800 text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
              <th className="p-4">Reaction / Experiment Title</th>
              <th className="p-4">Yield (%)</th>
              <th className="p-4">Temperature</th>
              <th className="p-4">Catalyst</th>
              <th className="p-4">Solvent</th>
              <th className="p-4">Source Literature</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-xs font-mono">
            {mockExperiments.map((exp) => (
              <tr key={exp.id} className="hover:bg-slate-800/60 transition-colors">
                <td className="p-4 font-bold text-slate-200">{exp.reaction_name}</td>
                <td className="p-4 text-emerald-400 font-bold">{exp.yield_pct}%</td>
                <td className="p-4 text-slate-300">{exp.temp}</td>
                <td className="p-4 text-cyan-400 font-semibold">{exp.catalyst}</td>
                <td className="p-4 text-slate-400">{exp.solvent}</td>
                <td className="p-4 text-slate-300 font-sans">
                  <span className="px-1.5 py-0.5 text-[10px] font-mono text-cyan-400 bg-cyan-950 border border-cyan-800 rounded mr-1.5 font-bold">
                    [{exp.citation_id}]
                  </span>
                  {exp.paper}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
