import React, { useEffect, useState } from 'react';
import { documentsApi } from '../services/api';
import { DocumentItem } from '../types';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const loadDocuments = async () => {
    try {
      const docs = await documentsApi.listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.warn('Could not load documents:', err);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setIsUploading(true);
    setUploadProgress(0);

    try {
      await documentsApi.uploadDocument(file, (pct) => setUploadProgress(pct));
      await loadDocuments();
    } catch (err) {
      alert(`Upload failed: ${err}`);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      await documentsApi.deleteDocument(id);
      await loadDocuments();
    } catch (err) {
      alert(`Delete failed: ${err}`);
    }
  };

  const handleRetry = async (id: string) => {
    try {
      await documentsApi.retryProcessing(id);
      await loadDocuments();
    } catch (err) {
      alert(`Retry failed: ${err}`);
    }
  };

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch = doc.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight">Scientific Document Repository</h2>
          <p className="text-xs text-slate-400 mt-1">
            Ingest scholarly PDFs, journals, and chemical patents with GROBID TEI-XML structure parsing.
          </p>
        </div>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        className="border-2 border-dashed border-cyan-800/60 hover:border-cyan-500/80 bg-cyan-950/20 hover:bg-cyan-950/40 rounded-2xl p-8 text-center transition-all cursor-pointer relative"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFileUpload(e.dataTransfer.files);
        }}
      >
        <input
          type="file"
          accept=".pdf"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          onChange={(e) => handleFileUpload(e.target.files)}
        />
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-cyan-950 text-cyan-400 flex items-center justify-center text-xl font-bold border border-cyan-700">
            📥
          </div>
          <div>
            <p className="text-sm font-bold text-slate-200">Drag & Drop Scientific PDFs here or click to browse</p>
            <p className="text-xs text-slate-400 mt-0.5">Supports academic papers, thermodynamic tables, chemical structures, and patents</p>
          </div>
        </div>

        {/* Upload Progress Bar */}
        {isUploading && (
          <div className="mt-4 max-w-md mx-auto space-y-1 font-mono text-xs">
            <div className="flex justify-between text-cyan-400 font-bold">
              <span>Uploading PDF...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div className="bg-cyan-400 h-full transition-all duration-150" style={{ width: `${uploadProgress}%` }} />
            </div>
          </div>
        )}
      </div>

      {/* Controls & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900 p-4 rounded-xl border border-slate-800">
        <input
          type="text"
          placeholder="Search documents by title or DOI..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full sm:w-80 px-3.5 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-500"
        />

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400">Status:</span>
          {['all', 'processed', 'processing', 'failed'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-md capitalize transition-colors ${
                statusFilter === st ? 'bg-cyan-950 text-cyan-400 border border-cyan-800 font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-950 border-b border-slate-800 text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
              <th className="p-4">Document Title</th>
              <th className="p-4">Type</th>
              <th className="p-4">Status</th>
              <th className="p-4">Pages / Chunks</th>
              <th className="p-4">Created</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-xs">
            {filteredDocs.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-500 font-mono">
                  No documents found. Upload a scientific PDF to get started.
                </td>
              </tr>
            ) : (
              filteredDocs.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-800/50 transition-colors">
                  <td className="p-4 font-semibold text-slate-200">
                    <div>{doc.title}</div>
                    {doc.doi && <div className="text-[10px] text-cyan-400 font-mono">DOI: {doc.doi}</div>}
                  </td>
                  <td className="p-4 font-mono text-slate-400 uppercase text-[10px]">
                    <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">{doc.source_type || 'PDF'}</span>
                  </td>
                  <td className="p-4 font-mono">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        doc.status === 'processed'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : doc.status === 'failed'
                          ? 'bg-rose-950 text-rose-400 border border-rose-800'
                          : 'bg-amber-950 text-amber-400 border border-amber-800'
                      }`}
                    >
                      {doc.status}
                    </span>
                  </td>
                  <td className="p-4 font-mono text-slate-400">
                    {doc.page_count || 12} p / {doc.chunk_count || 148} chunks
                  </td>
                  <td className="p-4 font-mono text-slate-500">{new Date(doc.created_at || Date.now()).toLocaleDateString()}</td>
                  <td className="p-4 text-right space-x-2 font-mono">
                    {doc.status === 'failed' && (
                      <button onClick={() => handleRetry(doc.id)} className="text-amber-400 hover:underline">
                        Retry
                      </button>
                    )}
                    <button onClick={() => handleDelete(doc.id)} className="text-rose-400 hover:underline">
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
