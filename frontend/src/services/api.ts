import axios from 'axios';
import {
  CitationItem,
  ChemicalEntity,
  DocumentItem,
  HealthResponse,
  IngestionJob,
} from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const healthApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const res = await apiClient.get<HealthResponse>('/health');
    return res.data;
  },
  getReadiness: async (): Promise<HealthResponse> => {
    const res = await apiClient.get<HealthResponse>('/health/readiness');
    return res.data;
  },
  getLiveness: async (): Promise<{ status: string }> => {
    const res = await apiClient.get<{ status: string }>('/health/liveness');
    return res.data;
  },
};

export const documentsApi = {
  listDocuments: async (): Promise<DocumentItem[]> => {
    const res = await apiClient.get<DocumentItem[]>('/documents');
    return res.data;
  },
  uploadDocument: async (file: File, onProgress?: (pct: number) => void): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append('file', file);

    const res = await apiClient.post<DocumentItem>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress?.(pct);
        }
      },
    });
    return res.data;
  },
  deleteDocument: async (id: string): Promise<boolean> => {
    await apiClient.delete(`/documents/${id}`);
    return true;
  },
  retryProcessing: async (id: string): Promise<DocumentItem> => {
    const res = await apiClient.post<DocumentItem>(`/documents/${id}/retry`);
    return res.data;
  },
};

export const searchApi = {
  searchHybrid: async (query: string, topK: number = 10): Promise<any> => {
    const res = await apiClient.post('/search/hybrid', {
      query_text: query,
      top_k: topK,
    });
    return res.data;
  },
};

export const chemistryApi = {
  canonicalize: async (identifier: string): Promise<ChemicalEntity> => {
    const res = await apiClient.post<ChemicalEntity>('/chemistry/canonicalize', {
      query: identifier,
    });
    return res.data;
  },
};

export const citationsApi = {
  assignCitations: async (chunks: any[]): Promise<{ citations: CitationItem[]; llm_context_text: string }> => {
    const res = await apiClient.post('/citations/assign', { chunks });
    return res.data;
  },
  validateResponse: async (generatedText: string, validCitations: CitationItem[]): Promise<any> => {
    const res = await apiClient.post('/citations/validate', {
      generated_text: generatedText,
      valid_citations: validCitations,
    });
    return res.data;
  },
  getEvidenceMapping: async (citationId: string, viewportWidth: number, viewportHeight: number): Promise<any> => {
    const res = await apiClient.post('/citations/evidence', {
      citation_id: citationId,
      viewport_width: viewportWidth,
      viewport_height: viewportHeight,
    });
    return res.data;
  },
};
