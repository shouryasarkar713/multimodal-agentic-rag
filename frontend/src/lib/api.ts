import { Document, Session, Message, QueryTrace } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'test-api-key-123';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers();
  if (API_KEY) {
    headers.append('X-API-Key', API_KEY);
  }
  
  if (options?.body && !(options.body instanceof FormData)) {
    headers.append('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...Object.fromEntries(headers.entries()),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  async uploadDocument(file: File): Promise<{ document_id: string; filename: string; status: string; message: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return apiFetch('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  },

  async getDocuments(): Promise<{ documents: Document[] }> {
    return apiFetch('/documents');
  },

  async getDocument(id: string): Promise<Document & { chunk_counts?: { text: number; table: number; image: number } }> {
    return apiFetch(`/documents/${id}`);
  },

  async deleteDocument(id: string): Promise<{ message: string }> {
    return apiFetch(`/documents/${id}`, {
      method: 'DELETE',
    });
  },

  async getDocumentFigures(id: string): Promise<{ figures: { chunk_id: string; page_number: number; caption: string; image_url: string }[] }> {
    return apiFetch(`/documents/${id}/figures`);
  },

  async createSession(title?: string): Promise<Session> {
    return apiFetch('/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  },

  async getSessions(): Promise<{ sessions: Session[] }> {
    return apiFetch('/sessions');
  },

  async deleteSession(id: string): Promise<{ message: string }> {
    return apiFetch(`/sessions/${id}`, {
      method: 'DELETE',
    });
  },

  async getMessages(sessionId: string): Promise<{ messages: Message[] }> {
    return apiFetch(`/sessions/${sessionId}/messages`);
  },

  async chat(req: { session_id: string; query: string; document_ids?: string[] }): Promise<{
    message_id: string;
    content: string;
    citations: any[];
    figure_refs: any[];
    confidence: number;
    trace_id: string;
    intent: string;
    retrieval_types: string[];
  }> {
    return apiFetch('/chat', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async getTrace(traceId: string): Promise<QueryTrace> {
    return apiFetch(`/traces/${traceId}`);
  },

  async exportMarkdown(messageId: string): Promise<Blob> {
    const headers = new Headers();
    if (API_KEY) {
      headers.append('X-API-Key', API_KEY);
    }
    headers.append('Content-Type', 'application/json');

    const res = await fetch(`${API_BASE}/export/markdown`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message_id: messageId }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }

    return res.blob();
  },
};
