import React from 'react';

const mockJobs = [
  {
    id: 'job-101',
    name: 'PDF Ingestion & GROBID Parsing',
    target: 'Thermodynamics_Ethanol.pdf',
    stage: 'indexing',
    progress: 100,
    status: 'completed',
    started: '10:00:15',
  },
  {
    id: 'job-102',
    name: 'Chemical Structure Recognition (RDKit)',
    target: 'Batch_Upload_2024.zip',
    stage: 'embedding',
    progress: 75,
    status: 'running',
    started: '10:05:22',
  },
];

export const JobsPage: React.FC = () => {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-black text-white tracking-tight">Background Processing & Ingestion Jobs</h2>
        <p className="text-xs text-slate-400 mt-1">
          Asynchronous Celery/Redis worker queues for document parsing, chunking, 3072d vector embedding, and chemical normalization.
        </p>
      </div>

      <div className="space-y-4">
        {mockJobs.map((job) => (
          <div key={job.id} className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3 shadow-md">
            <div className="flex items-center justify-between font-mono text-xs">
              <div className="flex items-center gap-3">
                <span className="font-bold text-slate-200">{job.name}</span>
                <span className="text-slate-400">({job.target})</span>
              </div>
              <span
                className={`px-2.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                  job.status === 'completed' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-cyan-950 text-cyan-400 border border-cyan-800 animate-pulse'
                }`}
              >
                {job.status}
              </span>
            </div>

            <div className="space-y-1 font-mono text-xs">
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Stage: <strong className="text-cyan-400">{job.stage}</strong></span>
                <span>{job.progress}%</span>
              </div>
              <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                <div className="bg-cyan-400 h-full transition-all duration-300" style={{ width: `${job.progress}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
