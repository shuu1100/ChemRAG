import React, { useState } from 'react';

export interface ViewportCoords {
  page_number: number;
  x_pct: number;
  y_pct: number;
  width_pct: number;
  height_pct: number;
  viewport_x0: number;
  viewport_y0: number;
  viewport_x1: number;
  viewport_y1: number;
}

export interface PDFViewerOverlayProps {
  citationId: string;
  documentTitle: string;
  pdfUrl: string;
  pageNumber: number;
  coords?: ViewportCoords;
  snippetText?: string;
  doi?: string;
  onClose?: () => void;
}

export const PDFViewerOverlay: React.FC<PDFViewerOverlayProps> = ({
  citationId,
  documentTitle,
  pdfUrl,
  pageNumber,
  coords,
  snippetText,
  doi,
  onClose,
}) => {
  const [zoom, setZoom] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(pageNumber);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.2, 3.0));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.2, 0.5));
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="flex flex-col w-full max-w-5xl h-[90vh] bg-white border border-slate-200 rounded-xl shadow-2xl overflow-hidden">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 text-xs font-mono font-bold text-cyan-700 bg-cyan-50 border border-cyan-300 rounded">
              {citationId}
            </span>
            <div>
              <h3 className="text-base font-bold text-slate-900">{documentTitle}</h3>
              <p className="text-xs text-slate-500">
                Page {currentPage} {doi ? `• DOI: ${doi}` : ''}
              </p>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleZoomOut}
              className="px-2.5 py-1 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded"
              title="Zoom Out"
            >
              -
            </button>
            <span className="text-xs text-slate-600 min-w-[45px] text-center font-mono font-bold">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              className="px-2.5 py-1 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded"
              title="Zoom In"
            >
              +
            </button>
            <button
              onClick={handleRotate}
              className="px-2.5 py-1 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded"
              title="Rotate 90°"
            >
              ↻ {rotation}°
            </button>
            <button
              onClick={onClose}
              className="ml-4 px-3 py-1 text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white rounded transition-colors shadow-2xs"
            >
              Close
            </button>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* PDF Viewport Container */}
          <div className="flex-1 relative bg-slate-100/70 overflow-auto p-6 flex justify-center">
            <div
              className="relative bg-white shadow-lg transition-transform origin-top duration-200 border border-slate-200"
              style={{
                width: `${800 * zoom}px`,
                height: `${1100 * zoom}px`,
                transform: `rotate(${rotation}deg)`,
              }}
            >
              {/* Mock/Rendered PDF Page */}
              <iframe
                src={`${pdfUrl}#page=${currentPage}`}
                className="w-full h-full border-none"
                title="PDF Document Viewport"
              />

              {/* Bounding Box Highlight Overlay */}
              {coords && (
                <div
                  className="absolute border-2 border-amber-500 bg-amber-400/25 animate-pulse rounded pointer-events-none transition-all"
                  style={{
                    left: `${coords.x_pct}%`,
                    top: `${coords.y_pct}%`,
                    width: `${coords.width_pct}%`,
                    height: `${coords.height_pct}%`,
                  }}
                >
                  <span className="absolute -top-6 left-0 px-1.5 py-0.5 text-[10px] font-bold font-mono text-slate-900 bg-amber-400 rounded">
                    {citationId}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Snippet & Provenance Sidebar */}
          <div className="w-80 border-l border-slate-200 bg-white p-5 flex flex-col gap-4 overflow-y-auto">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Source Text Snippet
            </h4>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 font-mono leading-relaxed whitespace-pre-wrap">
              {snippetText || 'No raw snippet available.'}
            </div>

            {coords && (
              <div className="space-y-2 text-xs text-slate-500 border-t border-slate-200 pt-3">
                <p className="font-semibold text-slate-800">Spatial Bounding Box Coordinates</p>
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px] bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">
                  <div>X0: {coords.viewport_x0}px</div>
                  <div>Y0: {coords.viewport_y0}px</div>
                  <div>W: {coords.width_pct}%</div>
                  <div>H: {coords.height_pct}%</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
