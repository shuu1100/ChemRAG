import React, { useEffect, useState } from 'react';
import { JobsIcon } from '../components/common/Icons';
import { jobsApi } from '../services/api';
import { IngestionJob } from '../types';

export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const data = await jobsApi.listJobs();
      setJobs(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err: any) {
      console.warn('Jobs API error:', err);
      setError(err?.message || 'Could not load background ingestion jobs');
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleRetryJob = async (jobId: string) => {
    try {
      await jobsApi.retryJob(jobId);
      fetchJobs();
    } catch (err: any) {
      alert(`Retry failed: ${err?.message || 'Unknown error'}`);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <JobsIcon size={22} className="text-cyan-600" />
            <span>Processing Pipeline & Background Jobs</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Asynchronous background worker pipeline for document layout parsing, GROBID TEI extraction, chemical-aware chunking, vector embedding, and pgvector indexing.
          </p>
        </div>
        <button
          onClick={fetchJobs}
          className="px-3.5 py-1.5 text-xs font-mono font-bold text-cyan-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs self-start sm:self-auto"
        >
          🔄 Refresh Status
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono">
          ⚠️ {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500">
              <th className="p-4">Job ID</th>
              <th className="p-4">Document ID</th>
              <th className="p-4">Current Stage</th>
              <th className="p-4">Progress</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs font-mono">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="p-12 text-center text-slate-400">
                  <div className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-cyan-600 border-t-transparent mb-2" />
                  <p>Fetching active ingestion jobs...</p>
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-12 text-center text-slate-400">
                  <p className="text-base font-bold text-slate-700 mb-1">No Active or Historical Jobs</p>
                  <p className="text-xs">Upload a scientific PDF in the Document Library to trigger background pipeline processing.</p>
                </td>
              </tr>
            ) : (
              jobs.map((job: any) => {
                const jobState = job.state || job.status || 'pending';
                const currentPhase = job.current_phase || job.current_stage || 'processing';
                const progressPct = Math.round(job.progress_pct || job.progress || 0);

                return (
                  <tr key={job.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 font-bold text-slate-900">{job.id.slice(0, 8)}...</td>
                    <td className="p-4 text-slate-600">{(job as any).document_id ? (job as any).document_id.slice(0, 8) + '...' : 'Doc'}</td>
                    <td className="p-4 text-cyan-700 font-bold uppercase">{currentPhase}</td>
                    <td className="p-4">
                      <div className="w-32 bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200 mb-1">
                        <div className="bg-cyan-600 h-full transition-all" style={{ width: `${progressPct}%` }} />
                      </div>
                      <span className="text-[10px] text-slate-500 font-bold">{progressPct}% completed</span>
                    </td>
                    <td className="p-4">
                      <span
                        className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          jobState === 'completed'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-300'
                            : jobState === 'failed'
                            ? 'bg-rose-50 text-rose-700 border border-rose-300'
                            : 'bg-amber-50 text-amber-700 border border-amber-300 animate-pulse'
                        }`}
                      >
                        {jobState}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      {jobState === 'failed' && (
                        <button
                          onClick={() => handleRetryJob(job.id)}
                          className="text-amber-600 hover:underline font-bold text-xs"
                        >
                          Retry Job
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default JobsPage;
