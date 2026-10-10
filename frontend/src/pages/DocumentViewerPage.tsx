import React, { useState } from 'react';
import { PDFViewerOverlay } from '../components/citations/PDFViewerOverlay';

export const DocumentViewerPage: React.FC = () => {
  const [selectedCitation, setSelectedCitation] = useState<string>('CIT-001');
  const [showModal, setShowModal] = useState<boolean>(true);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">PDF Evidence & Provenance Viewer</h2>
          <p className="text-xs text-slate-500 mt-1">
            Auditable citation evidence mapping with spatial PDF bounding box overlays and viewport alignment.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg shadow-sm"
        >
          Open Evidence Overlay
        </button>
      </div>

      {/* Embedded Evidence Viewer Demo Container */}
      <div className="p-6 bg-white border border-slate-200 rounded-2xl space-y-4 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 text-xs font-mono font-bold text-cyan-700 bg-cyan-50 border border-cyan-200 rounded">
            Active Citation: {selectedCitation}
          </span>
          <span className="text-xs text-slate-800">
            Document: <strong>Thermodynamic Properties of Ethanol-Water Mixtures</strong> (Page 3)
          </span>
        </div>

        {showModal && (
          <PDFViewerOverlay
            citationId={selectedCitation}
            documentTitle="Thermodynamic Properties of Ethanol-Water Mixtures"
            pdfUrl="/api/v1/documents/sample/file"
            pageNumber={3}
            coords={{
              page_number: 3,
              x_pct: 10.0,
              y_pct: 15.0,
              width_pct: 75.0,
              height_pct: 12.0,
              viewport_x0: 80,
              viewport_y0: 165,
              viewport_x1: 680,
              viewport_y1: 297,
            }}
            snippetText="Ethanol (CAS 64-17-5, formula C2H6O) has a boiling point of 78.37 °C and density of 0.789 g/cm³ at 20 °C."
            doi="10.1021/acs.jced.1c00001"
            onClose={() => setShowModal(false)}
          />
        )}
      </div>
    </div>
  );
};
