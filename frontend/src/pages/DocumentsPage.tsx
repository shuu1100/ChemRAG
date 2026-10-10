import React, { useEffect, useState } from 'react';
import { DocumentsIcon, PlusIcon, SearchIcon } from '../components/common/Icons';
import { documentsApi } from '../services/api';
import { DocumentItem } from '../types';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadDocuments = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const docs = await documentsApi.listDocuments();
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (err: any) {
      console.warn('Backend documents API error:', err);
      setLoadError(err?.message || 'Failed to fetch document corpus from backend');
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Only .pdf scientific papers are accepted.');
      return;
    }
    setUploadError(null);
    setIsUploading(true);
    setUploadProgress(10);

    try {
      await documentsApi.uploadDocument(file, (pct) => setUploadProgress(pct));
      await loadDocuments();
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || err?.message || 'Upload failed');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to remove this document from the workspace?')) return;
    try {
      await documentsApi.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      alert(`Delete failed: ${err?.message || 'Unknown error'}`);
    }
  };

  const handleRetry = async (id: string) => {
    try {
      await documentsApi.retryProcessing(id);
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: 'processing' } : d))
      );
      setTimeout(loadDocuments, 2000);
    } catch (err: any) {
      alert(`Retry failed: ${err?.message || 'Unknown error'}`);
    }
  };

  const filteredDocs = documents.filter((doc) => {
    const title = doc.title || (doc as any).filename || '';
    const doi = doc.doi || '';
    const matchesSearch = title.toLowerCase().includes(searchQuery.toLowerCase()) || doi.toLowerCase().includes(searchQuery.toLowerCase());
    const docStatus = doc.status || (doc as any).processing_state || 'completed';
    const matchesStatus = statusFilter === 'all' || docStatus === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <DocumentsIcon size={22} className="text-cyan-600" />
            <span>Scientific Document Library</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Ingest scholarly PDFs, journals, and chemical patents with GROBID TEI-XML structure parsing and RDKit chemistry indexing.
          </p>
        </div>
        <button
          onClick={loadDocuments}
          disabled={isLoading}
          className="px-3.5 py-1.5 text-xs font-mono font-bold text-cyan-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs flex items-center gap-1.5 self-start sm:self-auto"
        >
          🔄 Refresh Corpus
        </button>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        className="border-2 border-dashed border-cyan-300 hover:border-cyan-500 bg-white/90 hover:bg-cyan-50/50 rounded-xl p-8 text-center transition-all cursor-pointer relative shadow-sm"
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
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-full bg-cyan-50 text-cyan-600 flex items-center justify-center border border-cyan-200 shadow-2xs">
            <PlusIcon size={24} />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800">Drag & Drop Scientific PDFs here or click to browse</p>
            <p className="text-xs text-slate-500 mt-0.5">Supports academic papers, thermodynamic tables, chemical structures, and patents</p>
          </div>
        </div>

        {/* Upload Progress Bar */}
        {isUploading && (
          <div className="mt-4 max-w-md mx-auto space-y-1 font-mono text-xs">
            <div className="flex justify-between text-cyan-700 font-bold">
              <span>Uploading PDF to backend...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div className="bg-cyan-600 h-full transition-all duration-150" style={{ width: `${uploadProgress}%` }} />
            </div>
          </div>
        )}

        {uploadError && (
          <p className="mt-3 text-xs font-mono font-bold text-rose-600 bg-rose-50 border border-rose-200 py-1.5 px-3 rounded-lg max-w-md mx-auto">
            ⚠️ {uploadError}
          </p>
        )}
      </div>

      {loadError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono flex items-center justify-between shadow-sm">
          <span>⚠️ {loadError}</span>
          <button onClick={loadDocuments} className="px-3 py-1 bg-rose-600 text-white font-bold rounded-md hover:bg-rose-700">
            Retry Connection
          </button>
        </div>
      )}

      {/* Controls & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full sm:w-80">
          <input
            type="text"
            placeholder="Search documents by title or DOI..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-cyan-500 focus:bg-white font-sans shadow-2xs"
          />
          <SearchIcon size={16} className="absolute left-3 top-2.5 text-slate-400" />
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-500">Filter Status:</span>
          {['all', 'completed', 'processing', 'failed'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-md capitalize transition-colors ${
                statusFilter === st ? 'bg-cyan-50 text-cyan-700 border border-cyan-300 font-bold' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500">
              <th className="p-4">Document Title</th>
              <th className="p-4">Type</th>
              <th className="p-4">Status</th>
              <th className="p-4">Pages / Chunks</th>
              <th className="p-4">Ingestion Date</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="p-12 text-center text-slate-400 font-mono">
                  <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-cyan-600 border-t-transparent mb-2" />
                  <p>Loading document corpus from backend...</p>
                </td>
              </tr>
            ) : filteredDocs.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-400 font-mono">
                  No matching documents found. Upload a scientific PDF to populate your corpus.
                </td>
              </tr>
            ) : (
              filteredDocs.map((doc) => {
                const docTitle = doc.title || (doc as any).filename || 'Untitled Document';
                const docStatus = doc.status || (doc as any).processing_state || 'completed';
                const pageCount = (doc as any).page_count || 1;
                const chunkCount = (doc as any).chunk_count || 0;
                const createdAt = doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Recent';

                return (
                  <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 font-semibold text-slate-800">
                      <div className="text-sm text-slate-900">{docTitle}</div>
                      {doc.doi && <div className="text-[11px] text-cyan-700 font-mono mt-0.5">DOI: {doc.doi}</div>}
                    </td>
                    <td className="p-4 font-mono text-slate-500 uppercase text-[10px]">
                      <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 font-bold">
                        {doc.source_type || 'PDF'}
                      </span>
                    </td>
                    <td className="p-4 font-mono">
                      <span
                        className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          (docStatus as string) === 'completed' || (docStatus as string) === 'processed'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-300'
                            : (docStatus as string) === 'failed'
                            ? 'bg-rose-50 text-rose-700 border border-rose-300'
                            : 'bg-amber-50 text-amber-700 border border-amber-300 animate-pulse'
                        }`}
                      >
                        {docStatus}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-slate-600">
                      {pageCount} {pageCount === 1 ? 'page' : 'pages'} / {chunkCount} {chunkCount === 1 ? 'chunk' : 'chunks'}
                    </td>
                    <td className="p-4 font-mono text-slate-500">{createdAt}</td>
                    <td className="p-4 text-right space-x-3 font-mono">
                      <a
                        href={`/api/v1/documents/${doc.id}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-cyan-600 hover:underline font-bold"
                      >
                        PDF
                      </a>
                      {docStatus === 'failed' && (
                        <button onClick={() => handleRetry(doc.id)} className="text-amber-600 hover:underline font-bold">
                          Retry
                        </button>
                      )}
                      <button onClick={() => handleDelete(doc.id)} className="text-rose-600 hover:underline font-bold">
                        Remove
                      </button>
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

export default DocumentsPage;
