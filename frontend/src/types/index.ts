/**
 * ChemRAG — Frontend TypeScript Definitions
 */

export type AppEnvironment = 'development' | 'staging' | 'production';

export interface SystemServiceStatus {
  name: string;
  status: 'ok' | 'degraded' | 'unavailable';
  detail?: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'unavailable';
  env: string;
  version: string;
  uptime_seconds: number;
  timestamp: string;
  services: SystemServiceStatus[];
}

export interface DocumentItem {
  id: string;
  title: string;
  source_type: string;
  file_hash_sha256: string;
  file_size_bytes: number;
  status: 'pending' | 'processing' | 'processed' | 'failed' | 'archived';
  created_at: string;
  updated_at: string;
  page_count?: number;
  chunk_count?: number;
  error_message?: string;
  metadata?: Record<string, any>;
  authors?: string[];
  doi?: string;
}

export interface CitationItem {
  citation_id: string;
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number?: number;
  section_title?: string;
  bbox?: { x0: number; y0: number; x1: number; y1: number };
  confidence: number;
  raw_text: string;
  doi?: string;
}

export interface AgentStepTrace {
  agent_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'bypassed' | 'blocked';
  timestamp: string;
  summary: string;
  metrics?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  citations?: CitationItem[];
  agent_trace?: AgentStepTrace[];
  confidence_score?: number;
  chemistry_validated?: boolean;
  contained_entities?: string[];
}

export interface ChemicalEntity {
  id: string;
  canonical_name: string;
  smiles: string;
  inchikey?: string;
  inchi?: string;
  formula?: string;
  molecular_weight?: number;
  iupac_name?: string;
}

export interface ExperimentRecord {
  id: string;
  title: string;
  reaction_name?: string;
  yield_pct?: number;
  temperature_c?: number;
  catalyst?: string;
  solvent?: string;
  document_title: string;
  citation_id?: string;
}

export interface IngestionJob {
  id: string;
  document_id: string;
  document_title: string;
  stage: 'parsing' | 'chunking' | 'embedding' | 'indexing' | 'completed' | 'failed';
  progress_pct: number;
  started_at: string;
  error?: string;
}

export interface EvaluationMetric {
  metric_name: string;
  score: number;
  target_threshold: number;
  status: 'passed' | 'warning' | 'failed';
}

export interface AppSettings {
  llm_provider: 'openai' | 'anthropic';
  llm_model: string;
  embedding_model: string;
  vector_ef_search: number;
  safety_guardrails_enabled: boolean;
  allow_in_memory_fallback: boolean;
  citation_entailment_threshold: number;
}
