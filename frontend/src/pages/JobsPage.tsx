import React from 'react';
import { JobsIcon } from '../components/common/Icons';

export const JobsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <JobsIcon size={22} className="text-cyan-600" />
          <span>Processing Pipeline & Background Jobs</span>
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Asynchronous background worker queues for document parsing, chunking, 3072d vector embedding, and chemical structure normalization.
        </p>
      </div>

      <div className="p-8 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm text-center max-w-2xl mx-auto">
        <div className="w-12 h-12 rounded-xl bg-cyan-50 text-cyan-600 border border-cyan-200 flex items-center justify-center mx-auto shadow-2xs">
          <JobsIcon size={24} />
        </div>
        <div className="space-y-2">
          <h3 className="text-base font-bold text-slate-900">No Active Ingestion Jobs</h3>
          <p className="text-xs text-slate-500 leading-relaxed font-sans">
            When scientific papers are uploaded to the Document Library, background pipeline progress (GROBID TEI extraction, RDKit structure parsing, vector embedding) will appear here in real time.
          </p>
        </div>
        <div className="pt-2">
          <span className="inline-block px-3 py-1 text-[11px] font-mono text-cyan-700 bg-slate-50 border border-slate-200 rounded-full font-bold">
            Background Queue: Idle • Connected to GET /api/v1/documents/jobs/:id
          </span>
        </div>
      </div>
    </div>
  );
};

export default JobsPage;
