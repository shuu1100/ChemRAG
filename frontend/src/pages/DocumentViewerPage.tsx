import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PDFViewerOverlay } from '../components/citations/PDFViewerOverlay';
import { documentsApi } from '../services/api';
import { DocumentItem } from '../types';

export const DocumentViewerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>(() => searchParams.get('documentId') || '');
  const [currentPage, setCurrentPage] = useState<number>(() => {
    const p = parseInt(searchParams.get('page') || '1', 10);
    return isNaN(p) || p < 1 ? 1 : p;
  });
  const [selectedCitation, setSelectedCitation] = useState<string>(() => searchParams.get('citationId') || 'CIT-001');
  const [showModal, setShowModal] = useState<boolean>(false);
  const [zoom, setZoom] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);

  useEffect(() => {
    documentsApi.listDocuments().then((docs) => {
      setDocuments(docs);
      if (!selectedDocId && docs.length > 0) {
        setSelectedDocId(docs[0].id);
      }
    }).catch((err) => {
      console.warn('Failed to load documents:', err);
    });
  }, []);

  // Update selected doc if URL params change
  useEffect(() => {
    const urlDocId = searchParams.get('documentId');
    if (urlDocId && urlDocId !== selectedDocId) {
      setSelectedDocId(urlDocId);
    }
    const urlPage = parseInt(searchParams.get('page') || '1', 10);
    if (!isNaN(urlPage) && urlPage >= 1) {
      setCurrentPage(urlPage);
    }
    const urlCit = searchParams.get('citationId');
    if (urlCit) {
      setSelectedCitation(urlCit);
    }
  }, [searchParams]);

  const activeDoc = documents.find((d) => d.id === selectedDocId) || documents[0];
  const docTitle = activeDoc?.title || searchParams.get('title') || 'Scientific Paper';
  const pdfUrl = selectedDocId ? `/api/v1/documents/${selectedDocId}/file` : '';

  const handleSelectDoc = (id: string) => {
    setSelectedDocId(id);
    setCurrentPage(1);
    setSearchParams({ documentId: id, page: '1' });
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">PDF Evidence & Provenance Viewer</h2>
          <p className="text-xs text-slate-500 mt-1">
            Auditable citation evidence mapping with spatial PDF viewport alignment, page jumping, and text provenance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {documents.length > 0 && (
            <select
              value={selectedDocId}
              onChange={(e) => handleSelectDoc(e.target.value)}
              className="px-3 py-1.5 text-xs font-bold text-slate-800 bg-white border border-slate-300 rounded-lg shadow-2xs focus:ring-2 focus:ring-cyan-500"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title || d.id}
                </option>
              ))}
            </select>
          )}

          {pdfUrl && (
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg shadow-sm cursor-pointer"
            >
              Open Overlay Modal
            </button>
          )}
        </div>
      </div>

      {/* Embedded Live Viewer Container */}
      <div className="p-6 bg-white border border-slate-200 rounded-2xl space-y-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 text-xs font-mono font-bold text-cyan-700 bg-cyan-50 border border-cyan-200 rounded">
              Citation: {selectedCitation}
            </span>
            <span className="text-xs text-slate-800">
              Document: <strong>{docTitle}</strong> (Page {currentPage})
            </span>
          </div>

          {/* Controls Bar */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded border border-slate-300">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="px-2 py-0.5 text-xs font-bold text-slate-700 hover:bg-slate-200 disabled:opacity-40 rounded cursor-pointer"
                title="Previous Page"
              >
                ◀
              </button>
              <span className="text-xs font-mono font-bold px-1 text-slate-700 min-w-[32px] text-center">
                p. {currentPage}
              </span>
              <button
                type="button"
                onClick={() => setCurrentPage((p) => p + 1)}
                className="px-2 py-0.5 text-xs font-bold text-slate-700 hover:bg-slate-200 rounded cursor-pointer"
                title="Next Page"
              >
                ▶
              </button>
            </div>

            <button
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}
              className="px-2.5 py-1 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded cursor-pointer"
              title="Zoom Out"
            >
              -
            </button>
            <span className="text-xs text-slate-600 min-w-[45px] text-center font-mono font-bold">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(3.0, z + 0.2))}
              className="px-2.5 py-1 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded cursor-pointer"
              title="Zoom In"
            >
              +
            </button>
            <button
              onClick={() => setRotation((r) => (r + 90) % 360)}
              className="px-2.5 py-1 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded cursor-pointer"
              title="Rotate 90°"
            >
              ↻ {rotation}°
            </button>
            {pdfUrl && (
              <a
                href={`${pdfUrl}#page=${currentPage}`}
                target="_blank"
                rel="noreferrer"
                className="px-2.5 py-1 text-xs font-bold bg-cyan-50 hover:bg-cyan-100 text-cyan-800 border border-cyan-200 rounded cursor-pointer"
              >
                ↗ New Tab
              </a>
            )}
          </div>
        </div>

        {/* Live PDF Embed */}
        {pdfUrl ? (
          <div className="relative bg-slate-100/70 border border-slate-200 rounded-xl overflow-auto h-[75vh] flex justify-center p-4">
            <div
              className="relative bg-white shadow-lg transition-transform origin-top duration-200 border border-slate-200"
              style={{
                width: `${800 * zoom}px`,
                height: `${1100 * zoom}px`,
                transform: `rotate(${rotation}deg)`,
              }}
            >
              <iframe
                src={`${pdfUrl}#page=${currentPage}`}
                className="w-full h-full border-none"
                title="PDF Document Viewport"
              />
            </div>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-400 text-xs">
            No document selected or available. Please upload a PDF in Document Library first.
          </div>
        )}
      </div>

      {showModal && pdfUrl && (
        <PDFViewerOverlay
          citationId={selectedCitation}
          documentTitle={docTitle}
          pdfUrl={pdfUrl}
          pageNumber={currentPage}
          snippetText={`Evidence referenced from page ${currentPage} of ${docTitle}.`}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
};

export default DocumentViewerPage;
