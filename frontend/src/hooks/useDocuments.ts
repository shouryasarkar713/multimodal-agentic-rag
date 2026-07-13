import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import { Document } from '../lib/types';

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getDocuments();
      setDocuments(res.documents);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError('File is too large. Maximum size is 50 MB.');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      await api.uploadDocument(file);
      await fetchDocuments();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [fetchDocuments]);

  const deleteDoc = useCallback(async (id: string) => {
    try {
      setError(null);
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      setError(err.message || 'Failed to delete document');
    }
  }, []);

  const pollProcessingDocuments = useCallback(async () => {
    const processingIds = documents
      .filter((d) => d.status === 'processing')
      .map((d) => d.id);

    if (processingIds.length === 0) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    try {
      const updatedDocs = await Promise.all(
        processingIds.map(async (id) => {
          try {
            return await api.getDocument(id);
          } catch (e) {
            return null;
          }
        })
      );

      setDocuments((prev) =>
        prev.map((doc) => {
          const match = updatedDocs.find((u) => u && u.id === doc.id);
          if (match) {
            return {
              ...doc,
              status: match.status,
              title: match.title,
              authors: match.authors,
              total_pages: match.total_pages,
              error_message: match.error_message,
            };
          }
          return doc;
        })
      );
    } catch (err) {
      console.error('Error during status polling', err);
    }
  }, [documents]);

  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === 'processing');
    
    if (hasProcessing && !pollingTimerRef.current) {
      pollingTimerRef.current = setInterval(() => {
        pollProcessingDocuments();
      }, 5000);
    } else if (!hasProcessing && pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [documents, pollProcessingDocuments]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return {
    documents,
    loading,
    uploading,
    error,
    setError,
    fetchDocuments,
    uploadFile,
    deleteDoc,
  };
}
