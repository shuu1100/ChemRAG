import React from 'react';

export interface CitationBadgeProps {
  citationId: string;
  documentTitle?: string;
  pageNumber?: number;
  confidence?: number;
  onClick?: (citationId: string) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citationId,
  documentTitle = 'Source Document',
  pageNumber,
  confidence,
  onClick,
}) => {
  const formattedId = citationId.startsWith('[') ? citationId : `[${citationId}]`;

  return (
    <button
      type="button"
      onClick={() => onClick?.(citationId)}
      className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 text-xs font-bold font-mono text-cyan-700 bg-cyan-50 hover:bg-cyan-100 border border-cyan-300 rounded transition-colors shadow-2xs cursor-pointer"
      title={`${documentTitle}${pageNumber ? ` — Page ${pageNumber}` : ''}${confidence ? ` (Conf: ${(confidence * 100).toFixed(0)}%)` : ''}`}
    >
      <span>{formattedId}</span>
      {pageNumber && <span className="text-[10px] text-cyan-600 font-semibold">p.{pageNumber}</span>}
    </button>
  );
};
