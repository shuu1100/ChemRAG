import React from 'react';

export interface CitationBadgeProps {
  citationId: str;
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
      className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 text-xs font-semibold font-mono text-cyan-400 bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-700/50 rounded transition-colors shadow-sm cursor-pointer"
      title={`${documentTitle}${pageNumber ? ` — Page ${pageNumber}` : ''}${confidence ? ` (Conf: ${(confidence * 100).toFixed(0)}%)` : ''}`}
    >
      <span>{formattedId}</span>
      {pageNumber && <span className="text-[10px] text-cyan-300 opacity-80">p.{pageNumber}</span>}
    </button>
  );
};
