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
    formData.append('organization_id', '00000000-0000-0000-0000-000000000000');

    const res = await apiClient.post<any>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress?.(pct);
        }
      },
    });

    return {
      id: res.data.document_id || res.data.id,
      title: res.data.filename || file.name,
      source_type: 'PDF',
      file_hash_sha256: res.data.sha256_hash || '',
      file_size_bytes: res.data.file_size_bytes || file.size,
      status: res.data.status || 'pending',
      created_at: res.data.timestamp || new Date().toISOString(),
      updated_at: res.data.timestamp || new Date().toISOString(),
    };
  },
  deleteDocument: async (id: string): Promise<boolean> => {
    await apiClient.delete(`/documents/${id}`);
    return true;
  },
  retryProcessing: async (id: string): Promise<any> => {
    const res = await apiClient.post(`/documents/${id}/process`);
    return res.data;
  },
};

export const searchApi = {
  searchHybrid: async (query: string, topK: number = 10): Promise<any> => {
    const res = await apiClient.post('/search', {
      query_text: query,
      top_k: topK,
      rerank: true,
    });
    return res.data;
  },
};

export const chemistryApi = {
  canonicalize: async (identifier: string): Promise<ChemicalEntity> => {
    const isSmiles = identifier.includes('=') || identifier.includes('(') || identifier.length < 10;
    if (isSmiles) {
      try {
        const valRes = await apiClient.post('/chemistry/validate', { smiles: identifier });
        if (valRes.data.valid) {
          return {
            id: `chem-${Date.now()}`,
            canonical_name: identifier,
            smiles: valRes.data.canonical_smiles || identifier,
            inchikey: valRes.data.inchi_key || '',
            inchi: valRes.data.inchi || '',
            formula: valRes.data.molecular_formula || '',
            molecular_weight: valRes.data.molecular_weight || 0,
            iupac_name: identifier,
          };
        }
      } catch {
        // Fall through to resolve
      }
    }

    const res = await apiClient.post('/chemistry/resolve', {
      query: identifier,
      query_type: 'name',
    });

    const data = res.data;
    return {
      id: `chem-${data.cid || Date.now()}`,
      canonical_name: data.iupac_name || identifier,
      smiles: data.canonical_smiles || '',
      inchikey: data.inchi_key || '',
      inchi: data.inchi || '',
      formula: data.molecular_formula || '',
      molecular_weight: data.molecular_weight || 0,
      iupac_name: data.iupac_name || identifier,
    };
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
