export interface Document {
  id: string;
  filename: string;
  title?: string;
  authors?: string[];
  abstract?: string;
  total_pages: number;
  status: 'processing' | 'ready' | 'error';
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface Session {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number: number;
  section_title?: string;
  excerpt: string;
  relevance_score: number;
}

export interface FigureRef {
  chunk_id: string;
  document_id: string;
  image_path: string;
  caption: string;
  page_number: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[] | null;
  figure_refs?: FigureRef[] | null;
  confidence?: number | null;
  trace_id?: string | null;
  created_at: string;
}

export interface TraceStep {
  step_name: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
  metadata: any;
}

export interface QueryTrace {
  id: string;
  user_query: string;
  classified_intent?: string;
  steps: TraceStep[];
  total_duration_ms: number;
  langsmith_url?: string;
}
